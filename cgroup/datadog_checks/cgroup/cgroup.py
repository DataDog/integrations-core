# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import time

import psutil
from six import iteritems

from datadog_checks.checks import AgentCheck
from datadog_checks.config import _is_affirmative

class MountException(Exception):
    pass

class CGroupException(Exception):
    pass

DEFAULT_AD_CACHE_DURATION = 120
DEFAULT_PID_CACHE_DURATION = 120

GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate

CGROUP_METRICS = [
    {
        "cgroup": "memory",
        "file": "memory.stat",
        "metrics": {
            "cache": ("system.cgroups.mem.cache", GAUGE),
            "rss": ("system.cgroups.mem.rss", GAUGE),
            "swap": ("system.cgroups.mem.swap", GAUGE),
        },
        "to_compute": {
            # We only get these metrics if they are properly set, i.e. they are a "reasonable" value
            "system.cgroups.mem.limit": (["hierarchical_memory_limit"], lambda x: float(x) if float(x) < 2 ** 60 else None, GAUGE),
            "system.cgroups.mem.sw_limit": (["hierarchical_memsw_limit"], lambda x: float(x) if float(x) < 2 ** 60 else None, GAUGE),
            "system.cgroups.mem.in_use": (["rss", "hierarchical_memory_limit"], lambda x, y: float(x)/float(y) if float(y) < 2 ** 60 else None, GAUGE),
            "system.cgroups.mem.sw_in_use": (["swap", "rss", "hierarchical_memsw_limit"], lambda x, y, z: float(x + y)/float(z) if float(z) < 2 ** 60 else None, GAUGE)
        }
    },
    {
        "cgroup": "memory",
        "file": "memory.soft_limit_in_bytes",
        "metrics": {
            "softlimit": ("system.cgroups.mem.soft_limit", GAUGE),
        },
    },
    {
        "cgroup": "memory",
        "file": "memory.kmem.usage_in_bytes",
        "metrics": {
            "kmemusage": ("system.cgroups.kmem.usage", GAUGE),
        },
    },
    {
        "cgroup": "cpuacct",
        "file": "cpuacct.stat",
        "metrics": {
            "user": ("system.cgroups.cpu.user", RATE),
            "system": ("system.cgroups.cpu.system", RATE),
        },
    },
    {
        "cgroup": "cpuacct",
        "file": "cpuacct.usage",
        "metrics": {
            "usage": ("system.cgroups.cpu.usage", RATE),
        }
    },
    {
        "cgroup": "cpu",
        "file": "cpu.stat",
        "metrics": {
            "nr_throttled": ("system.cgroups.cpu.throttled", RATE)
        },
    },
    {
        "cgroup": "cpu",
        "file": "cpu.shares",
        "metrics": {
            "shares": ("system.cgroups.cpu.shares", GAUGE)
        },
    },
    {
        "cgroup": "blkio",
        "file": 'blkio.throttle.io_service_bytes',
        "metrics": {
            "io_read": ("system.cgroups.io.read_bytes", RATE),
            "io_write": ("system.cgroups.io.write_bytes", RATE),
        },
    },
]


class CgroupCheck(AgentCheck):
    """Collect metrics from cgroups."""
    def __init__(self, name, init_config, instances):
        super(Cgroup, self).__init__(name, init_config, instances)

        self._init = False

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

        # discover where cgroups sysfs is located
        self._procfs_path = init_config.get('procfs_path', '').rstrip('/') or self.agentConfig.get('procfs_path', '/proc').rstrip('/')
        self._root_path = init_config.get('root_path', '').rstrip('/') or self.agentConfig.get('root_path', '/').rstrip('/') or '/'
        self._mountpoints = self._get_mountpoints(CGROUP_METRICS)
        self.log.info("agentConfig: %s" % repr(self.agentConfig))
        self.log.info("procfs_path: %s" % self._procfs_path)

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

        self.log.info("found pids: %s" % repr(pids))
        for pid in pids:
            self._report_cgroup_metrics(pid, tags)

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


    def _report_cgroup_metrics(self, pid, tags):
        for cgroup in CGROUP_METRICS:
            try:
                cgroup_path = self._find_cgroup_from_proc(pid, cgroup['cgroup'])
                stat_file = self._find_cgroup_stat_file_path(cgroup['cgroup'], cgroup_path, cgroup['file'])
            except MountException as e:
                # We can't find a stat file
                self.warning(str(e))
                cgroup_stat_file_failures += 1
                if cgroup_stat_file_failures >= len(CGROUP_METRICS):
                    self.warning("Couldn't find the cgroup files. Skipping the CGROUP_METRICS for now.")
            except IOError as e:
                self.log.debug("Cannot read cgroup file, container likely raced to finish : %s", e)
            else:
                stats = self._parse_cgroup_file(stat_file)
                if stats:
                    cgroup_tags = tags + [
                        'cgroup_subsystem:{}'.format(cgroup['cgroup']),
                        'cgroup_path:{}'.format(cgroup_path)
                    ]

                    for key, (dd_key, metric_func) in cgroup['metrics'].iteritems():
                        if key in stats:
                            metric_func(self, dd_key, int(stats[key]), tags=cgroup_tags)

                    # Computed metrics
                    for mname, (key_list, fct, metric_func) in cgroup.get('to_compute', {}).iteritems():
                        values = [stats[key] for key in key_list if key in stats]
                        if len(values) != len(key_list):
                            self.log.debug("Couldn't compute {0}, some keys were missing. Required keys: {1}, found keys: {2}".format(mname, key_list, stats.keys()))
                            continue
                        value = fct(*values)
                        if value is not None:
                            metric_func(self, mname, value, tags=cgroup_tags)

    def _get_mountpoints(self, cgroup_metrics):
        mountpoints = {}
        for metric in cgroup_metrics:
            try:
                mountpoints[metric["cgroup"]] = self._find_cgroup(metric["cgroup"])
            except CGroupException as e:
                log.exception("Unable to find cgroup: %s", e)

        if not len(mountpoints):
            raise CGroupException("No cgroups were found!")

        return mountpoints

    def _find_cgroup(self, hierarchy):
        """Find the mount point for a specified cgroup hierarchy.
        Works with old style and new style mounts.
        An example of what the output of /proc/mounts looks like:
            cgroup /sys/fs/cgroup/cpuset cgroup rw,relatime,cpuset 0 0
            cgroup /sys/fs/cgroup/cpu cgroup rw,relatime,cpu 0 0
            cgroup /sys/fs/cgroup/cpuacct cgroup rw,relatime,cpuacct 0 0
            cgroup /sys/fs/cgroup/memory cgroup rw,relatime,memory 0 0
            cgroup /sys/fs/cgroup/devices cgroup rw,relatime,devices 0 0
            cgroup /sys/fs/cgroup/freezer cgroup rw,relatime,freezer 0 0
            cgroup /sys/fs/cgroup/blkio cgroup rw,relatime,blkio 0 0
            cgroup /sys/fs/cgroup/perf_event cgroup rw,relatime,perf_event 0 0
            cgroup /sys/fs/cgroup/hugetlb cgroup rw,relatime,hugetlb 0 0
        """
        with open(os.path.join(self._procfs_path, "mounts"), 'r') as fp:
            mounts = map(lambda x: x.split(), fp.read().splitlines())
        cgroup_mounts = filter(lambda x: x[2] == "cgroup", mounts)
        if len(cgroup_mounts) == 0:
            raise Exception(
                "Can't find mounted cgroups. If you run the Agent inside a container,"
                " please refer to the documentation.")
        # Old cgroup style
        if len(cgroup_mounts) == 1:
            return os.path.join(self._root_path, cgroup_mounts[0][1])

        candidate = None
        for _, mountpoint, _, opts, _, _ in cgroup_mounts:
            if any(opt == hierarchy for opt in opts.split(',')) and os.path.exists(mountpoint):
                if mountpoint.startswith("/host/"):
                    return os.path.join(self._root_path, mountpoint)
                candidate = mountpoint

        if candidate is not None:
            return os.path.join(self._root_path, candidate)
        raise CGroupException("Can't find mounted %s cgroups." % hierarchy)

    def _find_cgroup_stat_file_path(self, subsys, cgroup_path, file_path):
        """Find the path to the passed in cgroup file by walking the possible
        cgroupfs mountpoints
        """
        for mountpoint in self._mountpoints.itervalues():
            stat_file_path = os.path.join(mountpoint, cgroup_path)
            if subsys == mountpoint.split('/')[-1] and os.path.exists(stat_file_path):
                return os.path.join(stat_file_path, file_path)

            # CentOS7 will report `cpu,cpuacct` and then have the path on
            # `cpuacct,cpu`
            if 'cpuacct' in mountpoint and ('cpuacct' in subsys or 'cpu' in subsys):
                flipkey = subsys.split(',')
                flipkey = "{},{}".format(flipkey[1], flipkey[0]) if len(flipkey) > 1 else flipkey[0]
                mountpoint = os.path.join(os.path.split(mountpoint)[0], flipkey)
                stat_file_path = os.path.join(mountpoint, cgroup_path)
                if os.path.exists(stat_file_path):
                    return os.path.join(stat_file_path, file_path)

    def _find_cgroup_from_proc(self, pid, subsys):
        """Find the cgroup path of the specified pid for the specified subsystem (cgroup controller)
        """
        proc_path = os.path.join(self._procfs_path, str(pid), 'cgroup')
        with open(proc_path, 'r') as fp:
            lines = map(lambda x: x.split(':'), fp.read().splitlines())
            subsystems = dict(zip(map(lambda x: x[1], lines), map(self._parse_subsystem, lines)))

        if subsys not in subsystems and subsys == 'cpuacct':
            for form in "{},cpu", "cpu,{}":
                _subsys = form.format(subsys)
                if _subsys in subsystems:
                    subsys = _subsys
                    break

        # In Ubuntu Xenial, we've encountered containers with no `cpu`
        # cgroup in /proc/<pid>/cgroup
        if subsys == 'cpu' and subsys not in subsystems:
            for sub, mountpoint in subsystems.iteritems():
                if 'cpuacct' in sub:
                    subsystems['cpu'] = mountpoint
                    break

        if subsys in subsystems:
            return subsystems[subsys]

        raise MountException("Cannot find Docker '%s' cgroup directory. Be sure your system is supported." % subsys)

    def _parse_blkio_metrics(self, stats):
        """Parse the blkio metrics."""
        metrics = {
            'io_read': 0,
            'io_write': 0,
        }
        for line in stats:
            if 'Read' in line:
                metrics['io_read'] += int(line.split()[2])
            if 'Write' in line:
                metrics['io_write'] += int(line.split()[2])
        return metrics

    def _parse_cgroup_file(self, stat_file):
        """Parse a cgroup pseudo file for key/values."""
        self.log.debug("Opening cgroup file: %s" % stat_file)
        try:
            with open(stat_file, 'r') as fp:
                if 'blkio' in stat_file:
                    return self._parse_blkio_metrics(fp.read().splitlines())
                elif 'cpuacct.usage' in stat_file:
                    return dict({'usage': str(int(fp.read())/10000000)})
                elif 'memory.soft_limit_in_bytes' in stat_file:
                    value = int(fp.read())
                    # do not report kernel max default value (uint64 * 4096)
                    # see https://github.com/torvalds/linux/blob/5b36577109be007a6ecf4b65b54cbc9118463c2b/mm/memcontrol.c#L2844-L2845
                    # 2 ** 60 is kept for consistency of other cgroups metrics
                    if value < 2 ** 60:
                        return dict({'softlimit': value})
                elif 'memory.kmem.usage_in_bytes' in stat_file:
                    value = int(fp.read())
                    if value < 2 ** 60:
                        return dict({'kmemusage': value})
                elif 'cpu.shares' in stat_file:
                    value = int(fp.read())
                    return {'shares': value}
                else:
                    return dict(map(lambda x: x.split(' ', 1), fp.read().splitlines()))
        except IOError:
            # It is possible that the container got stopped between the API call and now.
            # Some files can also be missing (like cpu.stat) and that's fine.
            self.log.debug("Can't open %s. Its metrics will be missing." % stat_file)

    def _parse_subsystem(cls, line):
        """
        Parse cgroup path.
        - If the path is a slice (see https://access.redhat.com/documentation/en-US/Red_Hat_Enterprise_Linux/7/html/Resource_Management_Guide/sec-Default_Cgroup_Hierarchies.html)
          we return the path as-is (we still strip out any leading '/')
        - If 'docker' is in the path, it can be there once or twice:
          /docker/$CONTAINER_ID
          /docker/$USER_DOCKER_CID/docker/$CONTAINER_ID
          so we pick the last one.
        In /host/sys/fs/cgroup/$CGROUP_FOLDER/ cgroup/container IDs can be at the root
        or in a docker folder, so if we find 'docker/' in the path we don't strip it away.
        """
        if '.slice' in line[2]:
            return line[2].lstrip('/')
        i = line[2].rfind('docker')
        if i != -1:  # rfind returns -1 if docker is not found
            return line[2][i:]
        elif line[2][0] == '/':
            return line[2][1:]
        else:
            return line[2]
