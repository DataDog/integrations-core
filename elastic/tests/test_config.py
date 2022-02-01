# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import pytest
from six import PY2

from datadog_checks.base.errors import ConfigurationError
from datadog_checks.elastic import ESCheck
from datadog_checks.elastic.config import from_instance


@pytest.mark.unit
def test_from_instance_invalid():
    # missing url
    with pytest.raises(ConfigurationError):
        from_instance({})
    # empty url
    with pytest.raises(ConfigurationError):
        from_instance({'url': ''})


@pytest.mark.unit
def test_from_instance_defaults():
    c = from_instance({'url': 'http://example.com'})

    assert c.admin_forwarder is False
    assert c.pshard_stats is False
    assert c.pshard_graceful_to is False
    assert c.cluster_stats is False
    assert c.detailed_index_stats is False
    assert c.index_stats is False
    assert c.service_check_tags == ['host:example.com', 'port:None']
    assert c.tags == ['url:http://example.com']
    assert c.url == 'http://example.com'
    assert c.pending_task_stats is True


@pytest.mark.unit
def test_from_instance_cluster_stats():
    c = from_instance({'url': 'http://example.com', 'is_external': True})
    assert c.cluster_stats is True


@pytest.mark.unit
def test_from_instance_detailed_index_stats():
    c = from_instance({'url': 'http://example.com', 'detailed_index_stats': True})
    assert c.detailed_index_stats is True


@pytest.mark.unit
def test_from_instance():
    instance = {
        "username": "user",
        "password": "pass",
        "is_external": "yes",
        "detailed_index_stats": "yes",
        "url": "http://foo.bar",
        "tags": ["a", "b:c"],
    }
    c = from_instance(instance)
    assert c.admin_forwarder is False
    assert c.cluster_stats is True
    assert c.detailed_index_stats is True
    assert c.url == "http://foo.bar"
    assert c.tags == ["url:http://foo.bar", "a", "b:c"]
    assert c.service_check_tags == ["host:foo.bar", "port:None", "a", "b:c"]

    instance = {"url": "http://192.168.42.42:12999", "timeout": 15}
    c = from_instance(instance)
    assert c.cluster_stats is False
    assert c.url == "http://192.168.42.42:12999"
    assert c.tags == ["url:http://192.168.42.42:12999"]
    assert c.service_check_tags == ["host:192.168.42.42", "port:12999"]

    instance = {
        "username": "user",
        "password": "pass",
        "url": "https://foo.bar:9200",
        "ssl_verify": "true",
        "ssl_cert": "/path/to/cert.pem",
        "ssl_key": "/path/to/cert.key",
        "admin_forwarder": "1",
    }
    c = from_instance(instance)
    assert c.admin_forwarder is True
    assert c.cluster_stats is False
    assert c.detailed_index_stats is False
    assert c.url == "https://foo.bar:9200"
    assert c.tags == ["url:https://foo.bar:9200"]
    assert c.service_check_tags == ["host:foo.bar", "port:9200"]


@pytest.mark.parametrize(
    'invalid_custom_queries',
    [
        # Missing `data_path`
        [
            {
                'endpoint': '/_nodes',
                'columns': [
                    {
                        'value_path': 'total',
                        'name': 'elasticsearch.custom.metric',
                    },
                ],
                'tags': ['custom_tag:1'],
            },
        ],
        # Missing `columns`
        [
            {'endpoint': '/_nodes', 'data_path': '_nodes.', 'tags': ['custom_tag:1']},
        ],
        # Empty `dd_name` in `columns`
        [
            {
                'endpoint': '/_nodes',
                'data_path': '_nodes.',
                'columns': [
                    {
                        'value_path': 'total',
                        'name': '',
                    },
                ],
                'tags': ['custom_tag:1'],
            },
        ],
        # Empty `es_name`
        [
            {
                'endpoint': '/_nodes',
                'data_path': '_nodes.',
                'columns': [
                    {
                        'value_path': '',
                        'name': 'elasticsearch.custom.metric',
                    },
                ],
                'tags': ['custom_tag:1'],
            },
        ],
        # Missing `es_name` in `columns`
        [
            {
                'endpoint': '/_nodes',
                'data_path': '_nodes.',
                'columns': [
                    {
                        'value_path': 'total',
                        'name': 'elasticsearch.custom.metric',
                    },
                    {
                        'name': 'elasticsearch.custom.metric',
                    },
                ],
                'tags': ['custom_tag:1'],
            },
        ],
    ],
)
@pytest.mark.integration
@pytest.mark.skipif(PY2, reason='Test only available on Python 3')
def test_custom_query_invalid_config(dd_environment, dd_run_check, instance, aggregator, invalid_custom_queries):
    instance = deepcopy(instance)
    instance['custom_queries'] = invalid_custom_queries
    check = ESCheck('elastic', {}, instances=[instance])

    with pytest.raises(Exception):
        dd_run_check(check)
