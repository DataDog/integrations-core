# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import logging
import os

import pytest

from datadog_checks.base.checks.cgroup import CgroupMetricsScraper
from datadog_checks.dev.utils import running_on_windows_ci

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures', 'cgroup')


def metrics2dict(metrics):
    return dict(map(lambda x: [x[0], x[1:4]], metrics))


@pytest.fixture
def cgroup_fs(fs):
    fs.add_real_directory(FIXTURE_PATH)

    with open(os.path.join(FIXTURE_PATH, "mounts")) as f:
        fs.create_file('/proc/mounts', contents=f.read())

    fs.create_dir('/sys/fs/cgroup/blkio/system.slice/docker.service')
    fs.create_dir('/sys/fs/cgroup/cpu,cpuacct/system.slice/docker.service')
    fs.create_dir('/sys/fs/cgroup/memory/system.slice/docker.service')

    with open(os.path.join(FIXTURE_PATH, "proc_cgroup")) as f:
        fs.create_file('/proc/42/cgroup', contents=f.read())

    return fs


@pytest.mark.skipif(running_on_windows_ci(), reason='Test cannot be run on Windows CI')
class TestScraper:
    def test_default_mountpoint(self, cgroup_fs):
        scraper = CgroupMetricsScraper(procfs_path='/proc', root_path='/')
        assert scraper._mountpoints == {
            'memory': '/sys/fs/cgroup/memory',
            'cpuacct': '/sys/fs/cgroup/cpu,cpuacct',
            'cpu': '/sys/fs/cgroup/cpu,cpuacct',
            'blkio': '/sys/fs/cgroup/blkio',
        }

    def test_no_metrics_errors(self, cgroup_fs, caplog):
        scraper = CgroupMetricsScraper(procfs_path='/proc', root_path='/')
        with caplog.at_level(logging.WARNING):
            metrics = scraper.fetch_cgroup_metrics(42, [])

        assert len(caplog.records) == 0
        assert len(metrics) == 0  # none of the metric files are present

    def test_blkio_metrics(self, cgroup_fs):
        expected_tags = ['cgroup_subsystem:blkio', 'cgroup_path:system.slice/docker.service']

        with open(os.path.join(FIXTURE_PATH, "blkio")) as f:
            cgroup_fs.create_file(
                '/sys/fs/cgroup/blkio/system.slice/docker.service/blkio.throttle.io_service_bytes', contents=f.read()
            )

        scraper = CgroupMetricsScraper(procfs_path='/proc', root_path='/')
        metrics = scraper.fetch_cgroup_metrics(42, [])
        d = metrics2dict(metrics)
        assert d['system.cgroups.io.read_bytes'] == ('rate', 602112, expected_tags)
        assert d['system.cgroups.io.write_bytes'] == ('rate', 3281354752, expected_tags)

    def test_cpuacct_metrics(self, cgroup_fs):
        expected_tags = ['cgroup_subsystem:cpuacct', 'cgroup_path:system.slice/docker.service']

        with open(os.path.join(FIXTURE_PATH, "cpuacct_stat")) as f:
            cgroup_fs.create_file(
                '/sys/fs/cgroup/cpu,cpuacct/system.slice/docker.service/cpuacct.stat', contents=f.read()
            )

        scraper = CgroupMetricsScraper(procfs_path='/proc', root_path='/')
        metrics = scraper.fetch_cgroup_metrics(42, [])
        d = metrics2dict(metrics)
        assert d['system.cgroups.cpu.user'] == ('rate', 2160, expected_tags)
        assert d['system.cgroups.cpu.system'] == ('rate', 2206, expected_tags)

    def test_cpu_metrics(self, cgroup_fs):
        expected_tags = ['cgroup_subsystem:cpu', 'cgroup_path:system.slice/docker.service']

        with open(os.path.join(FIXTURE_PATH, "cpu_stat")) as f:
            cgroup_fs.create_file('/sys/fs/cgroup/cpu,cpuacct/system.slice/docker.service/cpu.stat', contents=f.read())

        scraper = CgroupMetricsScraper(procfs_path='/proc', root_path='/')
        metrics = scraper.fetch_cgroup_metrics(42, [])
        d = metrics2dict(metrics)
        assert d['system.cgroups.cpu.throttle_periods'] == ('rate', 100, expected_tags)
        assert d['system.cgroups.cpu.throttled'] == ('rate', 10, expected_tags)

    def test_memory_metrics(self, cgroup_fs):
        expected_tags = ['cgroup_subsystem:memory', 'cgroup_path:system.slice/docker.service']

        with open(os.path.join(FIXTURE_PATH, "memory_stat")) as f:
            cgroup_fs.create_file('/sys/fs/cgroup/memory/system.slice/docker.service/memory.stat', contents=f.read())

        scraper = CgroupMetricsScraper(procfs_path='/proc', root_path='/')
        metrics = scraper.fetch_cgroup_metrics(42, [])
        d = metrics2dict(metrics)
        assert d['system.cgroups.mem.cache'] == ('gauge', 12288, expected_tags)
        assert d['system.cgroups.mem.rss'] == ('gauge', 11247616, expected_tags)
        assert d['system.cgroups.mem.swap'] == ('gauge', 66888, expected_tags)

    def test_memory_computed_metrics(self, cgroup_fs):
        expected_tags = ['cgroup_subsystem:memory', 'cgroup_path:system.slice/docker.service']

        with open(os.path.join(FIXTURE_PATH, "memory_stat")) as f:
            cgroup_fs.create_file('/sys/fs/cgroup/memory/system.slice/docker.service/memory.stat', contents=f.read())

        scraper = CgroupMetricsScraper(procfs_path='/proc', root_path='/')
        metrics = scraper.fetch_cgroup_metrics(42, [])
        d = metrics2dict(metrics)
        assert d['system.cgroups.mem.limit'] == ('gauge', 104857600.0, expected_tags)
        assert d['system.cgroups.mem.sw_limit'] == ('gauge', 209715200.0, expected_tags)
        assert d['system.cgroups.mem.in_use'] == ('gauge', 11247616.0 / 104857600.0, expected_tags)
        assert d['system.cgroups.mem.sw_in_use'] == ('gauge', float(11247616 + 66888) / float(209715200), expected_tags)
