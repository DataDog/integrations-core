# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import unittest

from datadog_checks.checks import AgentCheck
from datadog_checks.stubs import aggregator


def test_instance():
    """
    Simply assert the class can be insantiated
    """
    AgentCheck()


class TestTags:
    def test_default_string(self):
        check = AgentCheck()
        tag = 'default:string'
        tags = [tag]

        normalized_tags = check._normalize_tags(tags, None)
        normalized_tag = normalized_tags[0]

        assert normalized_tags is not tags
        assert normalized_tag == tag.encode('utf-8')

    def test_bytes_string(self):
        check = AgentCheck()
        tag = b'bytes:string'
        tags = [tag]

        normalized_tags = check._normalize_tags(tags, None)
        normalized_tag = normalized_tags[0]

        assert normalized_tags is not tags
        # Ensure no new allocation occurs
        assert normalized_tag is tag

    def test_unicode_string(self):
        check = AgentCheck()
        tag = u'unicode:string'
        tags = [tag]

        normalized_tags = check._normalize_tags(tags, None)
        normalized_tag = normalized_tags[0]

        assert normalized_tags is not tags
        assert normalized_tag == tag.encode('utf-8')


class LimitedCheck(AgentCheck):
    DEFAULT_METRIC_LIMIT = 10


class TestLimits(unittest.TestCase):
    def tearDown(self):
        aggregator.reset()

    def test_metric_limit_gauges(self):
        check = LimitedCheck()
        assert check.get_warnings() == []

        for i in range(0, 10):
            check.gauge("metric", 0)
        assert len(check.get_warnings()) == 0
        assert len(aggregator.metrics("metric")) == 10

        for i in range(0, 10):
            check.gauge("metric", 0)
        assert len(check.get_warnings()) == 1
        assert len(aggregator.metrics("metric")) == 10

    def test_metric_limit_count(self):
        check = LimitedCheck()
        assert check.get_warnings() == []

        # Multiple calls for a single context should not trigger
        for i in range(0, 20):
            check.count("metric", 0, hostname="host-single")
        assert len(check.get_warnings()) == 0
        assert len(aggregator.metrics("metric")) == 20

        # Multiple contexts should trigger
        # Only 9 new contexts should pass through
        for i in range(0, 20):
            check.count("metric", 0, hostname="host-{}".format(i))
        assert len(check.get_warnings()) == 1
        assert len(aggregator.metrics("metric")) == 29
