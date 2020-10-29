# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import os
import re
import subprocess
import time
from collections import defaultdict

import psutil
from six import iteritems

from datadog_checks.base import AgentCheck
from datadog_checks.base.config import _is_affirmative
from datadog_checks.base.utils.platform import Platform

from .cache import DEFAULT_SHARED_PROCESS_LIST_CACHE_DURATION, ProcessListCache

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


DEFAULT_AD_CACHE_DURATION = 120
DEFAULT_PID_CACHE_DURATION = 120


ATTR_TO_METRIC = {
    'thr': 'threads',
    'cpu': 'cpu.pct',
    'cpu_norm': 'cpu.normalized_pct',
    'rss': 'mem.rss',
    'vms': 'mem.vms',
    'real': 'mem.real',
    'open_fd': 'open_file_descriptors',
    'open_handle': 'open_handles',  # win32 only
    # FIXME: namespace me correctly (8.x), io.r_count
    'r_count': 'ioread_count',
    # FIXME: namespace me correctly (8.x) io.r_bytes
    'w_count': 'iowrite_count',
    # FIXME: namespace me correctly (8.x) io.w_count
    'r_bytes': 'ioread_bytes',
    # FIXME: namespace me correctly (8.x) io.w_bytes
    'w_bytes': 'iowrite_bytes',
    # FIXME: namespace me correctly (8.x), ctx_swt.voluntary
    'ctx_swtch_vol': 'voluntary_ctx_switches',
    # FIXME: namespace me correctly (8.x), ctx_swt.involuntary
    'ctx_swtch_invol': 'involuntary_ctx_switches',
    'run_time': 'run_time',
    'mem_pct': 'mem.pct',
}

ATTR_TO_METRIC_RATE = {
    'minflt': 'mem.page_faults.minor_faults',
    'cminflt': 'mem.page_faults.children_minor_faults',
    'majflt': 'mem.page_faults.major_faults',
    'cmajflt': 'mem.page_faults.children_major_faults',
}


class ProcessCheck(AgentCheck):
    # Shared process list
    process_list_cache = ProcessListCache()

    def __init__(self, name, init_config, instances=None):
        super(ProcessCheck, self).__init__(name, init_config, instances)

        # ad stands for access denied
        # We cache the PIDs getting this error and don't iterate on them more often than `access_denied_cache_duration``
        # This cache is for all PIDs so it's global, but it should be refreshed by instance
        self.last_ad_cache_ts = {}
        self.ad_cache = set()
        self.access_denied_cache_duration = int(
            init_config.get('access_denied_cache_duration', DEFAULT_AD_CACHE_DURATION)
        )

        # By default cache the PID list for a while
        # Sometimes it's not wanted b/c it can mess with no-data monitoring
        # This cache is indexed per instance
        self.last_pid_cache_ts = {}
        self.pid_cache = {}
        self.pid_cache_duration = int(init_config.get('pid_cache_duration', DEFAULT_PID_CACHE_DURATION))

        self._conflicting_procfs = False
        self._deprecated_init_procfs = False
        if Platform.is_linux():
            procfs_path = init_config.get('procfs_path')
            if procfs_path:
                agent_procfs_path = datadog_agent.get_config('procfs_path')
                if agent_procfs_path and procfs_path != agent_procfs_path.rstrip('/'):
                    self._conflicting_procfs = True
                else:
                    self._deprecated_init_procfs = True
                    psutil.PROCFS_PATH = procfs_path

        # Process cache, indexed by instance
        self.process_cache = defaultdict(dict)

        self.process_list_cache.cache_duration = int(
            init_config.get('shared_process_list_cache_duration', DEFAULT_SHARED_PROCESS_LIST_CACHE_DURATION)
        )

    def should_refresh_ad_cache(self, name):
        now = time.time()
        return now - self.last_ad_cache_ts.get(name, 0) > self.access_denied_cache_duration

    def should_refresh_pid_cache(self, name):
        now = time.time()
        return now - self.last_pid_cache_ts.get(name, 0) > self.pid_cache_duration

    def find_pids(self, name, search_string, exact_match, ignore_ad=True):
        """
        Create a set of pids of selected processes.
        Search for search_string
        """
        if not self.should_refresh_pid_cache(name):
            return self.pid_cache[name]

        ad_error_logger = self.log.debug
        if not ignore_ad:
            ad_error_logger = self.log.error

        refresh_ad_cache = self.should_refresh_ad_cache(name)

        matching_pids = set()

        self.log.debug("Refreshing process list")

        # If refresh returns True, then the cache has been refreshed.
        # Otherwise the existing cache elements are used.
        if self.process_list_cache.refresh():
            self.log.debug("Set last ts to %s", self.process_list_cache.last_ts)
        else:
            self.log.debug("Using process list cache")

        with self.process_list_cache.read_lock():
            for proc in self.process_list_cache.elements:
                # Skip access denied processes
                if not refresh_ad_cache and proc.pid in self.ad_cache:
                    continue

                found = False
                for string in search_string:
                    try:
                        # FIXME 8.x: All has been deprecated
                        # from the doc, should be removed
                        if string == 'All':
                            found = True
                        if exact_match:
                            if os.name == 'nt':
                                if proc.name().lower() == string.lower():
                                    found = True
                            else:
                                if proc.name() == string:
                                    found = True

                        else:
                            cmdline = proc.cmdline()
                            if os.name == 'nt':
                                lstring = string.lower()
                                if re.search(lstring, ' '.join(cmdline).lower()):
                                    found = True
                            else:
                                if re.search(string, ' '.join(cmdline)):
                                    found = True
                    except psutil.NoSuchProcess:
                        # As the process list isn't necessarily scanned right after it's created
                        # (since we're using a shared cache), there can be cases where processes
                        # in the list are dead when an instance of the check tries to scan them.
                        self.log.debug('Process disappeared while scanning')
                    except psutil.AccessDenied as e:
                        ad_error_logger('Access denied to process with PID {}'.format(proc.pid))
                        ad_error_logger('Error: {}'.format(e))
                        if refresh_ad_cache:
                            self.ad_cache.add(proc.pid)
                        if not ignore_ad:
                            raise
                    else:
                        if refresh_ad_cache:
                            self.ad_cache.discard(proc.pid)
                        if found:
                            matching_pids.add(proc.pid)
                            break

            if not matching_pids:
                # Allow debug logging while preserving warning check state.
                # Uncaught psutil exceptions trigger an Error state
                try:
                    processes = sorted(proc.name() for proc in self.process_list_cache.elements)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                else:
                    self.log.debug(
                        "Unable to find process named %s among processes: %s", search_string, ', '.join(processes)
                    )

        self.pid_cache[name] = matching_pids
        self.last_pid_cache_ts[name] = time.time()
        if refresh_ad_cache:
            self.last_ad_cache_ts[name] = time.time()
        return matching_pids

    def psutil_wrapper(self, process, method, accessors, try_sudo, *args, **kwargs):
        """
        A psutil wrapper that is calling
        * psutil.method(*args, **kwargs) and returns the result
        OR
        * psutil.method(*args, **kwargs).accessor[i] for each accessors
        given in a list, the result being indexed in a dictionary
        by the accessor name
        """

        if accessors is None:
            result = None
        else:
            result = {}

        # Ban certain method that we know fail
        if method == 'num_fds' and not Platform.is_unix():
            return result
        elif method == 'num_handles' and not Platform.is_win32():
            return result

        try:
            res = getattr(process, method)(*args, **kwargs)
            if accessors is None:
                result = res
            else:
                for acc in accessors:
                    try:
                        result[acc] = getattr(res, acc)
                    except AttributeError:
                        self.log.debug("psutil.%s().%s attribute does not exist", method, acc)
        except (NotImplementedError, AttributeError):
            self.log.debug("psutil method %s not implemented", method)
        except psutil.AccessDenied:
            self.log.debug("psutil was denied access for method %s", method)
            if method == 'num_fds' and Platform.is_unix() and try_sudo:
                try:
                    # It is up the agent's packager to grant
                    # corresponding sudo policy on unix platforms
                    ls_args = ['sudo', 'ls', '/proc/{}/fd/'.format(process.pid)]
                    process_ls = subprocess.check_output(ls_args)
                    result = len(process_ls.splitlines())

                except subprocess.CalledProcessError as e:
                    self.log.exception(
                        "trying to retrieve %s with sudo failed with return code %s", method, e.returncode
                    )
                except Exception:
                    self.log.exception("trying to retrieve %s with sudo also failed", method)
        except psutil.NoSuchProcess:
            self.warning("Process %s disappeared while scanning", process.pid)

        return result

    def get_process_state(self, name, pids, try_sudo):
        st = defaultdict(list)

        # Remove from cache the processes that are not in `pids`
        cached_pids = set(self.process_cache[name].keys())
        pids_to_remove = cached_pids - pids
        for pid in pids_to_remove:
            del self.process_cache[name][pid]

        for pid in pids:
            st['pids'].append(pid)

            new_process = False
            # If the pid's process is not cached, retrieve it
            if pid not in self.process_cache[name] or not self.process_cache[name][pid].is_running():
                new_process = True
                try:
                    self.process_cache[name][pid] = psutil.Process(pid)
                    self.log.debug('New process in cache: %s', pid)
                # Skip processes dead in the meantime
                except psutil.NoSuchProcess:
                    self.warning('Process %s disappeared while scanning', pid)
                    # reset the PID cache now, something changed
                    self.last_pid_cache_ts[name] = 0
                    continue

            p = self.process_cache[name][pid]

            meminfo = self.psutil_wrapper(p, 'memory_info', ['rss', 'vms'], try_sudo)
            st['rss'].append(meminfo.get('rss'))
            st['vms'].append(meminfo.get('vms'))

            mem_percent = self.psutil_wrapper(p, 'memory_percent', None, try_sudo)
            st['mem_pct'].append(mem_percent)

            # will fail on win32 and solaris
            shared_mem = self.psutil_wrapper(p, 'memory_info', ['shared'], try_sudo).get('shared')
            if shared_mem is not None and meminfo.get('rss') is not None:
                st['real'].append(meminfo['rss'] - shared_mem)
            else:
                st['real'].append(None)

            ctxinfo = self.psutil_wrapper(p, 'num_ctx_switches', ['voluntary', 'involuntary'], try_sudo)
            st['ctx_swtch_vol'].append(ctxinfo.get('voluntary'))
            st['ctx_swtch_invol'].append(ctxinfo.get('involuntary'))

            st['thr'].append(self.psutil_wrapper(p, 'num_threads', None, try_sudo))

            cpu_percent = self.psutil_wrapper(p, 'cpu_percent', None, try_sudo)
            cpu_count = psutil.cpu_count()
            if not new_process:
                # psutil returns `0.` for `cpu_percent` the
                # first time it's sampled on a process,
                # so save the value only on non-new processes
                st['cpu'].append(cpu_percent)
                if cpu_count > 0 and cpu_percent is not None:
                    st['cpu_norm'].append(cpu_percent / cpu_count)
                else:
                    self.log.debug('could not calculate the normalized cpu pct, cpu_count: %s', cpu_count)
            st['open_fd'].append(self.psutil_wrapper(p, 'num_fds', None, try_sudo))
            st['open_handle'].append(self.psutil_wrapper(p, 'num_handles', None, try_sudo))

            ioinfo = self.psutil_wrapper(
                p, 'io_counters', ['read_count', 'write_count', 'read_bytes', 'write_bytes'], try_sudo
            )
            st['r_count'].append(ioinfo.get('read_count'))
            st['w_count'].append(ioinfo.get('write_count'))
            st['r_bytes'].append(ioinfo.get('read_bytes'))
            st['w_bytes'].append(ioinfo.get('write_bytes'))

            pagefault_stats = self.get_pagefault_stats(pid)
            if pagefault_stats is not None:
                (minflt, cminflt, majflt, cmajflt) = pagefault_stats
                st['minflt'].append(minflt)
                st['cminflt'].append(cminflt)
                st['majflt'].append(majflt)
                st['cmajflt'].append(cmajflt)
            else:
                st['minflt'].append(None)
                st['cminflt'].append(None)
                st['majflt'].append(None)
                st['cmajflt'].append(None)

            # calculate process run time
            create_time = self.psutil_wrapper(p, 'create_time', None, try_sudo)
            if create_time is not None:
                now = time.time()
                run_time = now - create_time
                st['run_time'].append(run_time)

        return st

    def get_pagefault_stats(self, pid):
        if not Platform.is_linux():
            return None

        def file_to_string(path):
            with open(path, 'r') as f:
                res = f.read()
            return res

        # http://man7.org/linux/man-pages/man5/proc.5.html
        try:
            data = file_to_string('/{}/{}/stat'.format(psutil.PROCFS_PATH, pid))
        except Exception:
            self.log.debug('error getting proc stats: file_to_string failed for /%s/%s/stat', psutil.PROCFS_PATH, pid)
            return None
        return (int(i) for i in data.split()[9:13])

    def _get_child_processes(self, pids):
        children_pids = set()
        for pid in pids:
            try:
                children = psutil.Process(pid).children(recursive=True)
                self.log.debug('%s children were collected for process %s', len(children), pid)
                for child in children:
                    children_pids.add(child.pid)
            except psutil.NoSuchProcess:
                pass

        return children_pids

    def check(self, _):
        name = self.instance.get('name', None)
        tags = self.instance.get('tags', [])
        exact_match = _is_affirmative(self.instance.get('exact_match', True))
        search_string = self.instance.get('search_string', None)
        ignore_ad = _is_affirmative(self.instance.get('ignore_denied_access', True))
        pid = self.instance.get('pid')
        pid_file = self.instance.get('pid_file')
        collect_children = _is_affirmative(self.instance.get('collect_children', False))
        user = self.instance.get('user', False)
        try_sudo = self.instance.get('try_sudo', False)

        if self._conflicting_procfs:
            self.warning(
                'The `procfs_path` defined in `process.yaml is different from the one defined in '
                '`datadog.conf` This is currently not supported by the Agent. Defaulting to the '
                'value defined in `datadog.conf`: %s',
                psutil.PROCFS_PATH,
            )
        elif self._deprecated_init_procfs:
            self.warning(
                'DEPRECATION NOTICE: Specifying `procfs_path` in process.yaml` is deprecated. '
                'Please specify it in `datadog.conf` instead'
            )

        if not isinstance(search_string, list) and pid is None and pid_file is None:
            raise ValueError('"search_string" or "pid" or "pid_file" parameter is required')

        # FIXME 8.x remove me
        if search_string is not None:
            if "All" in search_string:
                self.warning(
                    'Deprecated: Having "All" in your search_string will greatly reduce the '
                    'performance of the check and will be removed in a future version of the agent.'
                )

        if name is None:
            raise KeyError('The "name" of process groups is mandatory')

        if search_string is not None:
            pids = self.find_pids(name, search_string, exact_match, ignore_ad=ignore_ad)
        elif pid is not None:
            # we use Process(pid) as a means to search, if pid not found
            # psutil.NoSuchProcess is raised.
            pids = self._get_pid_set(pid)
        elif pid_file is not None:
            try:
                with open(pid_file, 'r') as file_pid:
                    pid_line = file_pid.readline().strip()
                    pids = self._get_pid_set(int(pid_line))
            except IOError as e:
                # pid file doesn't exist, assuming the process is not running
                self.log.debug('Unable to find pid file: %s', e)
                pids = set()
        else:
            raise ValueError('The "search_string" or "pid" options are required for process identification')

        if collect_children:
            pids.update(self._get_child_processes(pids))

        if user:
            pids = self._filter_by_user(user, pids)

        proc_state = self.get_process_state(name, pids, try_sudo)

        # FIXME 8.x remove the `name` tag
        tags.extend(['process_name:{}'.format(name), name])

        self.log.debug('ProcessCheck: process %s analysed', name)
        self.gauge('system.processes.number', len(pids), tags=tags)

        if len(pids) == 0:
            self.warning("No matching process '%s' was found", name)

        for attr, mname in iteritems(ATTR_TO_METRIC):
            vals = [x for x in proc_state[attr] if x is not None]
            # skip []
            if vals:
                sum_vals = sum(vals)
                if attr == 'run_time':
                    self.gauge('system.processes.{}.avg'.format(mname), sum_vals / len(vals), tags=tags)
                    self.gauge('system.processes.{}.max'.format(mname), max(vals), tags=tags)
                    self.gauge('system.processes.{}.min'.format(mname), min(vals), tags=tags)

                # FIXME 8.x: change this prefix?
                else:
                    self.gauge('system.processes.{}'.format(mname), sum_vals, tags=tags)
                    if mname in ['ioread_bytes', 'iowrite_bytes']:
                        self.monotonic_count('system.processes.{}_count'.format(mname), sum_vals, tags=tags)

        for attr, mname in iteritems(ATTR_TO_METRIC_RATE):
            vals = [x for x in proc_state[attr] if x is not None]
            if vals:
                self.rate('system.processes.{}'.format(mname), sum(vals), tags=tags)

        self._process_service_check(name, len(pids), self.instance.get('thresholds', None), tags)

    def _get_pid_set(self, pid):
        try:
            return {psutil.Process(pid).pid}
        except psutil.NoSuchProcess:
            return set()

    def _process_service_check(self, name, nb_procs, bounds, tags):
        """
        Report a service check, for each process in search_string.
        Report as OK if the process is in the warning thresholds
                   CRITICAL             out of the critical thresholds
                   WARNING              out of the warning thresholds
        """
        # FIXME 8.x remove the `process:name` tag
        service_check_tags = tags + ["process:{}".format(name)]
        status = AgentCheck.OK
        status_str = {AgentCheck.OK: "OK", AgentCheck.WARNING: "WARNING", AgentCheck.CRITICAL: "CRITICAL"}

        if not bounds and nb_procs < 1:
            status = AgentCheck.CRITICAL
        elif bounds:
            warning = bounds.get('warning', [1, float('inf')])
            critical = bounds.get('critical', [1, float('inf')])

            if warning[1] < nb_procs or nb_procs < warning[0]:
                status = AgentCheck.WARNING
            if critical[1] < nb_procs or nb_procs < critical[0]:
                status = AgentCheck.CRITICAL

        self.service_check(
            "process.up",
            status,
            tags=service_check_tags,
            message="PROCS {}: {} processes found for {}".format(status_str[status], nb_procs, name),
        )

    def _filter_by_user(self, user, pids):
        """
        Filter pids by it's username.
        :param user: string with name of system user
        :param pids: set of pids to filter
        :return: set of filtered pids
        """
        filtered_pids = set()
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                if proc.username() == user:
                    self.log.debug("Collecting pid %s belonging to %s", pid, user)
                    filtered_pids.add(pid)
                else:
                    self.log.debug("Discarding pid %s not belonging to %s", pid, user)
            except psutil.NoSuchProcess:
                pass

        return filtered_pids
