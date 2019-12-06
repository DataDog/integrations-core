# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import logging
from six import iteritems

from datadog_checks.checks import AgentCheck

GAUGE = AgentCheck.gauge
RATE = AgentCheck.rate

class MountException(Exception):
    pass

class CGroupException(Exception):
    pass

class CgroupMetricsScraper(object):
    def __init__(self, *args, **kwargs):
        # The scraper needs its own logger
        self.log = logging.getLogger(__name__)

        # `metrics_mapper` is a list of objects containing the metrics to capture and where to read them from
        self.metrics_mapper = [
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
                    "nr_periods": ("system.cgroups.cpu.throttle_periods", RATE),
                    "nr_throttled": ("system.cgroups.cpu.throttled", RATE)
                },
            },
            {
                "cgroup": "cpu",
                "file": "cpu.cfs_period_us",
                "metrics": {
                    "value": ("system.cgroups.cpu.cfs_period", GAUGE),
                },
            },
            {
                "cgroup": "cpu",
                "file": "cpu.cfs_quota_us",
                "metrics": {
                    "value": ("system.cgroups.cpu.cfs_quota", GAUGE),
                },
            },
            {
                "cgroup": "cpu",
                "file": "cpu.shares",
                "metrics": {
                    "value": ("system.cgroups.cpu.shares", GAUGE)
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

        # discover where cgroups sysfs is located
        self._procfs_path = kwargs['procfs_path'].rstrip('/')
        self._root_path = kwargs['root_path'].rstrip('/')
        self._mountpoints = kwargs.get('mountpoints') or self._get_mountpoints(self.metrics_mapper)

    def report_cgroup_metrics(self, pid, tags):
        for cgroup in self.metrics_mapper:
            try:
                cgroup_path = self._find_cgroup_from_proc(pid, cgroup['cgroup'])
                stat_file = self._find_cgroup_stat_file_path(cgroup['cgroup'], cgroup_path, cgroup['file'])
            except MountException as e:
                # We can't find a stat file
                self.log.warning(str(e))
                cgroup_stat_file_failures += 1
                if cgroup_stat_file_failures >= len(self.metrics_mapper):
                    self.log.warning("Couldn't find the cgroup files. Skipping cgroup-based metrics for now.")
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
