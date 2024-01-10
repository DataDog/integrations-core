# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
from typing import Any, Dict, List  # noqa: F401

import mock
import pytest

from datadog_checks.base import ConfigurationError
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.marklogic import MarklogicCheck
from datadog_checks.marklogic.config import Config
from datadog_checks.marklogic.parsers.resources import parse_resources

from .common import COMMON_TAGS, INSTANCE_FILTERS, read_fixture_file
from .metrics import HOST_STATUS_METRICS_GENERAL


def test_build_resource_filters():
    # type: () -> None
    conf = Config(INSTANCE_FILTERS)

    assert len(conf.resource_filters['included']) == 3
    assert conf.resource_filters['included'][0].resource_type == 'forest'
    assert conf.resource_filters['included'][0].regex.pattern == "^S[a-z]*"
    assert conf.resource_filters['included'][0].is_included is True
    assert conf.resource_filters['included'][0].group is None
    assert conf.resource_filters['included'][1].resource_type == 'database'
    assert conf.resource_filters['included'][1].regex.pattern == "^Doc"
    assert conf.resource_filters['included'][1].is_included is True
    assert conf.resource_filters['included'][1].group is None
    assert conf.resource_filters['included'][2].resource_type == 'server'
    assert conf.resource_filters['included'][2].regex.pattern == "Admin"
    assert conf.resource_filters['included'][2].is_included is True
    assert conf.resource_filters['included'][2].group == 'Default'

    assert len(conf.resource_filters['excluded']) == 1
    assert conf.resource_filters['excluded'][0].resource_type == 'forest'
    assert conf.resource_filters['excluded'][0].regex.pattern == "^Sch*"
    assert conf.resource_filters['excluded'][0].is_included is False
    assert conf.resource_filters['excluded'][0].group is None

    # Configuration error: no pattern
    with pytest.raises(ConfigurationError) as e:
        Config.build_resource_filters([{}])
        assert 'A resource filter requires at least a pattern and a resource_type' in str(e)
    # Configuration error: no resource_type
    with pytest.raises(ConfigurationError) as e:
        Config.build_resource_filters([{'pattern': 'abc'}])
        assert 'A resource filter requires at least a pattern and a resource_type' in str(e)
    # Configuration error: wrong resource_type
    with pytest.raises(ConfigurationError) as e:
        Config.build_resource_filters([{'pattern': 'abc', 'resource_type': 'datadog'}])
        assert 'Unknown resource_type: datadog' in str(e)


def test_get_resources_to_monitor():
    # type: () -> None
    check = MarklogicCheck('marklogic', {}, [INSTANCE_FILTERS])
    response_value = read_fixture_file('cluster-query.yaml')

    # Expected output when there is no exclude list
    complete_filtered = {
        'forest': [
            {'name': 'Security', 'id': '1112331563215633422', 'type': 'forest', 'uri': '/forests/Security'},
            {'name': 'Schemas', 'id': '5750304059804042419', 'type': 'forest', 'uri': '/forests/Schemas'},
        ],
        'database': [
            {'id': '5004266825873163057', 'name': 'Documents', 'type': 'database', 'uri': '/databases/Documents'}
        ],
        'host': [],
        'server': [
            {
                'name': 'Admin',
                'id': '9403936238896063877',
                'type': 'server',
                'uri': "/servers/Admin?group-id=Default",
                'group': 'Default',
            }
        ],
    }  # type: Dict[str, List[Any]]

    # Called in the check function
    check.resources = parse_resources(response_value)
    # Include list + exclude list
    filtered_res = check.get_resources_to_monitor()
    assert filtered_res == {
        'forest': [complete_filtered['forest'][0]],
        'database': complete_filtered['database'],
        'host': [],
        'server': complete_filtered['server'],
    }

    # No exclude list
    check._config.resource_filters['excluded'] = []
    filtered_res = check.get_resources_to_monitor()
    assert filtered_res == complete_filtered

    # Useless exclude list
    check._config.resource_filters['excluded'] = check._config.build_resource_filters(
        [{'resource_type': 'forest', 'pattern': 'Security', 'group': 'Default'}]
    )['excluded']
    filtered_res = check.get_resources_to_monitor()
    assert filtered_res == complete_filtered

    # No include list
    check._config.resource_filters['included'] = []
    filtered_res = check.get_resources_to_monitor()
    assert filtered_res == {
        'forest': [],
        'database': [],
        'host': [],
        'server': [],
    }


@mock.patch('datadog_checks.marklogic.api.MarkLogicApi.http_get', return_value=read_fixture_file('host_status.yaml'))
@mock.patch(
    'datadog_checks.marklogic.api.MarkLogicApi.get_requests_data', return_value=read_fixture_file('host_requests.yaml')
)
def test_collect_host_metrics(mock_requests, mock_status, aggregator):
    # type: (Any, Any, AggregatorStub) -> None
    check = MarklogicCheck('marklogic', {}, [INSTANCE_FILTERS])

    # Expected output when there is no exclude list
    check.resources_to_monitor = {
        'forest': [],
        'database': [],
        'host': [
            # Does not exist
            {'name': '9aea032c882e', 'id': '17797492400840985949', 'type': 'host', 'uri': '/hosts/9aea032c882e'},
            {'name': 'ff0fef449486', 'id': '3428441913043145991', 'type': 'host', 'uri': 'hosts/ff0fef449486'},
        ],
        'server': [],
    }

    check.collect_per_resource_metrics()

    expected_tags = COMMON_TAGS + ['marklogic_host_name:ff0fef449486']
    for m in HOST_STATUS_METRICS_GENERAL:
        aggregator.assert_metric(m, tags=expected_tags, count=1)
    for m in ['marklogic.requests.query-count', 'marklogic.requests.total-requests', 'marklogic.requests.update-count']:
        aggregator.assert_metric(m, tags=expected_tags, count=1)

    aggregator.assert_all_metrics_covered()


@mock.patch(
    'datadog_checks.marklogic.api.MarkLogicApi.http_get', return_value=read_fixture_file('bad_resource_storage.yaml')
)
def test_bad_resource_storage(mock_requests, aggregator, caplog):
    # type: (Any, Any, AggregatorStub) -> None
    caplog.at_level(logging.WARNING)
    check = MarklogicCheck('marklogic', {}, [INSTANCE_FILTERS])

    check.resources_to_monitor = {
        'forest': [
            {'id': '4259429487027269237', 'type': 'forest', 'name': 'Documents', 'uri': '/forests/Documents'},
        ],
        'database': [],
        'host': [],
        'server': [],
    }

    check.collect_per_resource_metrics()

    # This can happen when the database owning this forest is disabled
    assert "Status information unavailable for resource {" in caplog.text
    assert "Storage information unavailable for resource {" in caplog.text
