# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base import AgentCheck


class TestMetricHasTag:
    @pytest.mark.parametrize(
        'tags, at_least',
        [
            pytest.param([], 1, id='no tags'),
            pytest.param(['tag1:value1', 'tag2:value2'], 1, id='all tags'),
            pytest.param(['tag1:value1'], 1, id='some tags'),
            pytest.param(['tag3:value3'], 0, id='extra tag with at_least=0'),
        ],
    )
    def test_assert_metric_has_tags(self, aggregator, tags, at_least):
        check = AgentCheck()

        check.gauge('test.metric', 1, tags=['tag1:value1', 'tag2:value2'])
        aggregator.assert_metric_has_tags('test.metric', tags, at_least=at_least)

    def test_assert_metric_does_not_have_one_tag(self, aggregator):
        check = AgentCheck()
        check.gauge('test.metric', 1, tags=['tag1:value1', 'tag2:value2'])

        with pytest.raises(
            AssertionError, match="The metric 'test.metric' was found but not with the tag 'tag3:value3'."
        ):
            aggregator.assert_metric_has_tags('test.metric', ['tag1:value1', 'tag3:value3'])
