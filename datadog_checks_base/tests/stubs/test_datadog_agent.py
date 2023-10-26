# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

DEFAULT_EXTERNAL_TAGS = [
    ('hostname1', {'src1_name': ['test1:t1']}),
    ('hostname2', {'src2_name': ['test2:t2']}),
    ('hostname3', {'src3_name': ['test3:t3']}),
]


@pytest.mark.parametrize(
    'hostname, tags, raise_exception',
    [
        pytest.param('hostname1', {'src1_name': ['test1:t1']}, False, id="hostname1 and tags found"),
        pytest.param('hostname2', {'src2_name': ['test2:t2']}, False, id="hostname2 and tags found"),
        pytest.param('hostname3', {'src3_name': ['test3:t3']}, False, id="hostname3 and tags found"),
        pytest.param('hostname4', {'src4_name': ['test4:t4']}, True, id="hostname4 and tags not found"),
        pytest.param('hostname1', {'src2_name': ['test2:t2']}, True, id="hostname1 found and tags are wrong"),
    ],
)
def test_assert_external_tags(datadog_agent, hostname, tags, raise_exception):
    datadog_agent.set_external_tags(DEFAULT_EXTERNAL_TAGS)

    try:
        datadog_agent.assert_external_tags(hostname, tags)
    except AssertionError:
        if not raise_exception:
            raise


@pytest.mark.parametrize(
    'external_tags, count, raise_exception',
    [
        pytest.param(DEFAULT_EXTERNAL_TAGS, 3, False, id="correct count"),
        pytest.param([], 0, False, id="no tags"),
        pytest.param([('hostname1', {'src1_name': ['test1:t1']})], 1, False, id="one tag"),
        pytest.param([('hostname1', {'src1_name': ['test1:t1']})], 2, True, id="wrong count"),
    ],
)
def test_assert_external_tags_count(datadog_agent, external_tags, count, raise_exception):
    datadog_agent.set_external_tags(external_tags)

    try:
        datadog_agent.assert_external_tags_count(count)
    except AssertionError:
        if not raise_exception:
            raise
