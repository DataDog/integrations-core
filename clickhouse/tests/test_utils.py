# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.clickhouse import utils


@pytest.mark.unit
class TestErrorSanitizer:
    def test_clean(self):
        assert utils.ErrorSanitizer.clean('error..  Stack trace:  \n\n') == 'error.'

    def test_scrub(self):
        sanitizer = utils.ErrorSanitizer('foo')

        assert sanitizer.scrub('foobar') == '**********bar'

    def test_scrub_no_password(self):
        sanitizer = utils.ErrorSanitizer('')

        assert sanitizer.scrub('foobar') == 'foobar'


@pytest.mark.unit
@pytest.mark.parametrize(
    ['version', 'expected'],
    [
        ('25', [25]),
        ('25.1', [25, 1]),
        ('25.1.2', [25, 1, 2]),
        ('25.1.2.3', [25, 1, 2, 3]),
    ],
)
def test_parse_version(version: str, expected: list[int]):
    expected == utils.parse_version(version)


@pytest.mark.unit
def test_node_tag():
    assert utils.node_tag('node-1') == 'clickhouse_node:node-1'
    assert utils.CLUSTER_NODE_TAG == 'clickhouse_node'


@pytest.mark.unit
def test_cluster_aware_query_adds_node_tag():
    base = {
        'name': 'system.metrics',
        'query': 'SELECT value, metric FROM system.metrics',
        'columns': [{'name': 'value', 'type': 'gauge'}, {'name': 'metric', 'type': 'tag'}],
    }

    result = utils.cluster_aware_query(base)

    # Reads all replicas and selects hostName() as the per-node tag
    assert "clusterAllReplicas('default', system.metrics)" in result['query']
    assert 'hostName() AS clickhouse_node' in result['query']
    # The node column is appended as a tag column
    assert result['columns'][-1] == {'name': 'clickhouse_node', 'type': 'tag'}


@pytest.mark.unit
def test_cluster_aware_query_preserves_trailing_clause():
    base = {
        'name': 'system.errors',
        'query': 'SELECT value, name FROM system.errors WHERE value > 0',
        'columns': [{'name': 'value', 'type': 'gauge'}, {'name': 'name', 'type': 'tag'}],
    }

    result = utils.cluster_aware_query(base)

    assert "clusterAllReplicas('default', system.errors)" in result['query']
    assert 'WHERE value > 0' in result['query']
