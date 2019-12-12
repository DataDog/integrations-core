# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import time

import psutil
from six import iteritems

from datadog_checks.base import AgentCheck, _is_affirmative
from datadog_checks.base.checks.cgroup import CgroupMetricsScraper

DEFAULT_AD_CACHE_DURATION = 120
DEFAULT_PID_CACHE_DURATION = 120


class CgroupCheck(AgentCheck):
    """Collect metrics from cgroups."""

    def __init__(self, name, init_config, instances):
        super(CgroupCheck, self).__init__(name, init_config, instances)

        self._init = False
        self._procfs_path = init_config.get('procfs_path', '') or self.agentConfig.get('procfs_path', '/proc')
        self._root_path = init_config.get('root_path', '') or self.agentConfig.get('root_path', '/') or '/'

        self.scraper = CgroupMetricsScraper(procfs_path=self._procfs_path, root_path=self._root_path)

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

    def check(self, instance):
        name = instance.get('name', None)
        tags = instance.get('tags', [])
        exact_match = _is_affirmative(instance.get('exact_match', True))
        search_string = instance.get('search_string', None)
        ignore_ad = _is_affirmative(instance.get('ignore_denied_access', True))
        pid = instance.get('pid')
        pid_file = instance.get('pid_file')

        if name is None:
            raise KeyError('The "name" of process groups is mandatory')

        tags.extend(['process_name:{}'.format(name), name])

        if search_string is not None:
            pids = self._find_pids(name, search_string, exact_match, ignore_ad=ignore_ad)
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
                self.log.debug('Unable to find pid file: {}'.format(e))
                pids = set()
        else:
            raise ValueError('The "search_string" or "pid" options are required for process identification')

        self.log.info("Found matching pids for %s: %s" % (name, repr(pids)))
        for pid in pids:
            metrics = self.scraper.fetch_cgroup_metrics(pid, tags)

            for mname, metric_type, value, tags in metrics:
                self[metric_type](mname, value, tags=tags)

    def should_refresh_ad_cache(self, name):
        now = time.time()
        return now - self.last_ad_cache_ts.get(name, 0) > self.access_denied_cache_duration

    def should_refresh_pid_cache(self, name):
        now = time.time()
        return now - self.last_pid_cache_ts.get(name, 0) > self.pid_cache_duration

    def _find_pids(self, name, search_string, exact_match, ignore_ad=True):
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

        for proc in psutil.process_iter():
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
                    self.log.warning('Process disappeared while scanning')
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

        self.pid_cache[name] = matching_pids
        self.last_pid_cache_ts[name] = time.time()
        if refresh_ad_cache:
            self.last_ad_cache_ts[name] = time.time()
        return matching_pids
