# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck


class TestAssertHistogramBucket:
    def test_matches_on_bounds(self, aggregator):
        # Without bound tags, buckets with the same count differ only by their bounds
        check = AgentCheck()
        check.submit_histogram_bucket('test.histogram', 6, 0, 1, True, 'host', ['foo:bar'])
        check.submit_histogram_bucket('test.histogram', 6, 1, 2, True, 'host', ['foo:bar'])

        aggregator.assert_histogram_bucket('test.histogram', 6, 0, 1, True, 'host', ['foo:bar'], count=1)
        aggregator.assert_histogram_bucket('test.histogram', 6, 1, 2, True, 'host', ['foo:bar'], count=1)
        aggregator.assert_histogram_bucket('test.histogram', 6, None, None, True, 'host', ['foo:bar'], count=2)

    def test_wrong_bounds_fail(self, aggregator):
        check = AgentCheck()
        check.submit_histogram_bucket('test.histogram', 6, 0, 1, True, 'host', ['foo:bar'])

        with pytest.raises(AssertionError):
            aggregator.assert_histogram_bucket('test.histogram', 6, 1, 2, True, 'host', ['foo:bar'])
