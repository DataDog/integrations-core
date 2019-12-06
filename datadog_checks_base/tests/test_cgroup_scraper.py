# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock
import os
import pytest

from datadog_checks.base.checks.cgroup import CgroupMetricsScraper

FIXTURE_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'fixtures', 'cgroup')

class TestScraper():
    def test_default_mountpoint(self):
        with open(os.path.join(FIXTURE_PATH, "mounts")) as f:
            m = mock.mock_open(read_data=f.read())
            with mock.patch('builtins.open', m):
                scraper = CgroupMetricsScraper(procfs_path = '/proc', root_path = '/')