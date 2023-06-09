# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.elastic import ESCheck

from .common import URL, get_fixture_path

log = logging.getLogger('test_elastic')

pytestmark = pytest.mark.unit


def test__join_url():
    instance = {
        "url": "https://localhost:9444/elasticsearch-admin",
        "admin_forwarder": True,
    }
    check = ESCheck('elastic', {}, instances=[instance])

    adm_forwarder_joined_url = check._join_url("/stats", admin_forwarder=True)
    assert adm_forwarder_joined_url == "https://localhost:9444/elasticsearch-admin/stats"

    joined_url = check._join_url("/stats", admin_forwarder=False)
    assert joined_url == "https://localhost:9444/stats"


@pytest.mark.parametrize(
    'instance, url_fix',
    [
        pytest.param({'url': URL}, '_local/'),
        pytest.param({'url': URL, "cluster_stats": True, "slm_stats": True}, ''),
    ],
)
def test__get_urls(instance, url_fix):
    elastic_check = ESCheck('elastic', {}, instances=[instance])

    health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url = elastic_check._get_urls([])
    assert health_url == '/_cluster/health'
    assert stats_url == '/_cluster/nodes/' + url_fix + 'stats?all=true'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url is None
    assert slm_url is None

    health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url = elastic_check._get_urls([1, 0, 0])
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/' + url_fix + 'stats?all=true'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'
    assert slm_url is None

    health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url = elastic_check._get_urls([6, 0, 0])
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/' + url_fix + 'stats'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'
    assert slm_url is None

    health_url, stats_url, pshard_stats_url, pending_tasks_url, slm_url = elastic_check._get_urls([7, 4, 0])
    assert health_url == '/_cluster/health'
    assert stats_url == '/_nodes/' + url_fix + 'stats'
    assert pshard_stats_url == '/_stats'
    assert pending_tasks_url == '/_cluster/pending_tasks'
    assert slm_url == ('/_slm/policy' if instance.get('slm_stats') is True else None)


@pytest.mark.parametrize(
    'instance, expected_aws_host, expected_aws_service',
    [
        pytest.param(
            {'auth_type': 'aws', 'aws_region': 'foo', 'url': 'http://example.com'},
            'example.com',
            'es',
            id='aws_host_from_url',
        ),
        pytest.param(
            {'auth_type': 'aws', 'aws_region': 'foo', 'aws_host': 'foo.com', 'url': 'http://example.com'},
            'foo.com',
            'es',
            id='aws_host_custom_with_url',
        ),
        pytest.param(
            {'auth_type': 'aws', 'aws_region': 'foo', 'aws_service': 'es-foo', 'url': 'http://example.com'},
            'example.com',
            'es-foo',
            id='aws_service_custom',
        ),
    ],
)
def test_aws_auth_url(instance, expected_aws_host, expected_aws_service):
    check = ESCheck('elastic', {}, instances=[instance])

    assert getattr(check.http.options.get('auth'), 'aws_host', None) == expected_aws_host
    assert getattr(check.http.options.get('auth'), 'service', None) == expected_aws_service

    # make sure class attribute HTTP_CONFIG_REMAPPER is not modified
    assert 'aws_host' not in ESCheck.HTTP_CONFIG_REMAPPER


@pytest.mark.parametrize(
    'instance, expected_aws_host, expected_aws_service',
    [
        pytest.param({}, None, None, id='not aws auth'),
        pytest.param(
            {'auth_type': 'aws', 'aws_region': 'foo', 'aws_host': 'foo.com'},
            'foo.com',
            'es',
            id='aws_host_custom_no_url',
        ),
    ],
)
def test_aws_auth_no_url(instance, expected_aws_host, expected_aws_service):
    with pytest.raises(ConfigurationError):
        ESCheck('elastic', {}, instances=[instance])


def test_get_template_metrics(aggregator, instance, mock_http_response):
    mock_http_response(file_path=get_fixture_path('templates.json'))
    check = ESCheck('elastic', {}, instances=[instance])

    check._get_template_metrics(False, [])

    aggregator.assert_metric("elasticsearch.templates.count", value=6)
