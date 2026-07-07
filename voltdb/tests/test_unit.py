# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from typing import Any, Optional  # noqa: F401

import pytest
import requests

from datadog_checks.base import ConfigurationError
from datadog_checks.base.stubs.aggregator import AggregatorStub  # noqa: F401
from datadog_checks.base.stubs.datadog_agent import DatadogAgentStub  # noqa: F401
from datadog_checks.dev.utils import get_metadata_metrics
from datadog_checks.voltdb.check import VoltDBCheck
from datadog_checks.voltdb.client import Client
from datadog_checks.voltdb.config import Config
from datadog_checks.voltdb.types import Instance  # noqa: F401

from . import common

pytestmark = pytest.mark.unit

BASIC_INSTANCE = {'url': 'http://localhost:8000', 'username': 'doggo', 'password': 'doggopass'}  # type: Instance


def make_json_response(status_code, body):
    # type: (int, Any) -> requests.Response
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(body).encode()
    return response


class FakeClient(object):
    """A stand-in for Client that returns a canned response or raises a canned error."""

    def __init__(self, response=None, error=None):
        # type: (Optional[requests.Response], Optional[Exception]) -> None
        self._response = response
        self._error = error

    def request(self, procedure, parameters=None):
        # type: (str, Any) -> requests.Response
        if self._error is not None:
            raise self._error
        return self._response


@pytest.mark.parametrize(
    'instance, match',
    [
        pytest.param({'username': 'doggo', 'password': 'doggopass'}, 'url is required', id='url-missing'),
        pytest.param(
            {'url': 'http://:8080', 'username': 'doggo', 'password': 'doggopass'},
            'URL must contain a host',
            id='url-no-host',
        ),
        pytest.param({'url': 'http://:8080'}, 'username and password are required', id='creds-missing'),
        pytest.param(
            {'url': 'http://localhost:8080', 'username': 'doggo'},
            'username and password are required',
            id='creds-username-only',
        ),
        pytest.param(
            {'url': 'http://localhost:8080', 'password': 'doggopass'},
            'username and password are required',
            id='creds-password-only',
        ),
    ],
)
def test_config_errors(instance, match):
    # type: (Instance, str) -> None
    with pytest.raises(ConfigurationError, match=match):
        Config(instance)


@pytest.mark.parametrize(
    'instance, tags',
    [
        pytest.param(None, [], id='none'),
        pytest.param(['test:example'], ['test:example'], id='some'),
    ],
)
def test_custom_tags(instance, tags):
    # type: (Instance, Optional[list]) -> None
    instance = {'url': 'http://localhost:8000', 'username': 'doggo', 'password': 'doggopass'}
    if tags is not None:
        instance['tags'] = tags
    config = Config(instance)
    assert config.tags == tags


@pytest.mark.parametrize(
    'url, netloc',
    [
        pytest.param('http://localhost', ('localhost', 80), id='http'),
        pytest.param('https://localhost', ('localhost', 443), id='https'),
    ],
)
def test_default_port(url, netloc):
    # type: (str, tuple) -> None
    config = Config({'url': url, 'username': 'doggo', 'password': 'doggopass'})
    assert config.netloc == netloc


def test_metrics_with_fixtures(mock_results, aggregator, dd_run_check, instance_all):
    check = VoltDBCheck('voltdb', {}, [instance_all])
    dd_run_check(check)

    with open(os.path.join(common.HERE, 'fixtures', 'expected_metrics.json'), 'r') as f:
        metrics = json.load(f)

    for m in metrics:
        aggregator.assert_metric(m['name'], tags=m['tags'], metric_type=m['type'])

    # Ensure we're mapping the response correctly
    aggregator.assert_metric('voltdb.memory.tuple_count', value=2847267.0)
    aggregator.assert_metric('voltdb.memory.java.max_heap', value=531998.0)

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def test_password_hashed_defaults_to_false():
    # type: () -> None
    # Kills the core/ReplaceFalseWithTrue mutant at config.py:54 (password_hashed default False -> True).
    config = Config(BASIC_INSTANCE)
    assert config.password_hashed is False


def test_default_port_only_applies_to_https_scheme():
    # type: () -> None
    # Kills core/ReplaceComparisonOperator_Eq_GtE at config.py:71 (scheme == 'https' -> >=); 'httpz' >= 'https'.
    config = Config({'url': 'httpz://localhost', 'username': 'doggo', 'password': 'doggopass'})
    assert config.netloc == ('localhost', 80)


def test_instance_typed_dict_is_not_total():
    # type: () -> None
    # Kills core/ReplaceFalseWithTrue mutant at types.py:20 (total=False -> True).
    assert Instance.__total__ is False


def test_client_defaults_to_unhashed_password():
    # type: () -> None
    # Kills core/ReplaceFalseWithTrue at client.py:18 and core/AddNot at client.py:48 (Hashedpassword/Password swap).
    client = Client(
        url='http://localhost:8080', http_get=lambda *args, **kwargs: None, username='doggo', password='doggopass'
    )
    prepared = requests.Request(method='GET', url='http://localhost:8080/api/1.0/').prepare()
    prepared = client._auth(prepared)
    assert 'Password=doggopass' in prepared.url
    assert 'Hashedpassword' not in prepared.url


def test_client_request_json_encodes_non_string_parameters():
    # type: () -> None
    # Kills core/AddNot at client.py:30 and both mutants at client.py:31 (parameter presence & JSON-encoding).
    captured = {}

    def fake_http_get(url, auth=None, params=None):
        # type: (str, Any, dict) -> None
        captured.update(params)

    client = Client(url='http://localhost:8080', http_get=fake_http_get, username='doggo', password='doggopass')
    client.request('@Statistics', parameters=['MEMORY'])

    assert captured['Parameters'] == '["MEMORY"]'


def test_raise_for_status_with_details_wraps_http_error():
    # type: () -> None
    # Kills the core/ExceptionReplacer mutant at check.py:45 (except Exception -> except CosmicRayTestingException).
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    response = requests.Response()
    response.status_code = 500

    with pytest.raises(Exception, match='Error response from VoltDB'):
        check._raise_for_status_with_details(response)


def test_raise_for_status_with_details_ignores_invalid_json_details():
    # type: () -> None
    # Kills the core/ExceptionReplacer mutant at check.py:50 (except Exception -> except CosmicRayTestingException).
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    response = requests.Response()
    response.status_code = 500
    response._content = b'not valid json'

    with pytest.raises(Exception, match='Error response from VoltDB'):
        check._raise_for_status_with_details(response)


def test_fetch_version_uses_first_results_entry_and_locates_version_row():
    # type: () -> None
    # Kills core/NumberReplacer at check.py:63 (results[0] -> results[-1]), core/ZeroIterationForLoop at check.py:67,
    # and all core/ReplaceComparisonOperator_Eq_* / core/AddNot mutants at check.py:68 (column == 'VERSION').
    response = make_json_response(
        200,
        {
            'results': [
                {
                    'data': [
                        ['h0', 'ZEBRA', 'notaversion'],
                        ['h1', 'ALPHA', 'alsoignored'],
                        ['h2', 'VERSION', '9.4'],
                    ]
                },
                {'data': [['h9', 'VERSION', '0.1']]},
            ]
        },
    )
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    check._client = FakeClient(response=response)

    assert check._fetch_version() == '9.4.0'


def test_transform_version_splits_on_first_dot_only():
    # type: () -> None
    # Kills both core/NumberReplacer mutants at check.py:79 (split('.', 1) -> split('.', 2) or split('.', 0)).
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    assert check._transform_version('10.5.2') == '10.5.2'


def test_transform_version_pads_missing_patch_with_zero():
    # type: () -> None
    # Kills both core/ReplaceUnaryOperator_Delete_Not and core/AddNot mutants at check.py:84 (if not found).
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    assert check._transform_version('10.5') == '10.5.0'


def test_transform_version_malformed_returns_none():
    # type: () -> None
    # Kills the core/ExceptionReplacer mutant at check.py:80 (except ValueError -> except CosmicRayTestingException).
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    assert check._transform_version('10') is None


def test_submit_version_skipped_when_metadata_collection_disabled(datadog_agent):
    # type: (DatadogAgentStub) -> None
    # Kills the core/RemoveDecorator mutant at check.py:88 (removes @AgentCheck.metadata_entrypoint).
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    check.check_id = 'test'
    datadog_agent._config['enable_metadata_collection'] = False

    check._submit_version('9.4.1')

    datadog_agent.assert_metadata_count(0)


def test_check_can_connect_submits_version_metadata_when_version_present(aggregator, datadog_agent):
    # type: (AggregatorStub, DatadogAgentStub) -> None
    # Kills both core/ReplaceComparisonOperator_IsNot_Is and core/AddNot mutants at check.py:107
    # (if version is not None).
    response = make_json_response(200, {'results': [{'data': [['h0', 'VERSION', '9.4']]}]})
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    check.check_id = 'test'
    check._client = FakeClient(response=response)

    check._check_can_connect_and_submit_version()

    datadog_agent.assert_metadata('test', {'version.raw': '9.4.0'})


def test_check_can_connect_raises_and_records_critical_on_fetch_failure(aggregator):
    # type: (AggregatorStub) -> None
    # Kills the core/ExceptionReplacer mutant at check.py:100 (except Exception -> except CosmicRayTestingException).
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    check._client = FakeClient(error=Exception('boom'))

    with pytest.raises(Exception, match='boom'):
        check._check_can_connect_and_submit_version()

    aggregator.assert_service_check('voltdb.can_connect', VoltDBCheck.CRITICAL)


def test_execute_query_raw_returns_first_results_entry():
    # type: () -> None
    # Kills the core/NumberReplacer mutant at check.py:120 (results[0] -> results[-1]).
    response = make_json_response(
        200,
        {
            'results': [
                {'data': [['first-row']]},
                {'data': [['last-row']]},
            ]
        },
    )
    check = VoltDBCheck('voltdb', {}, [BASIC_INSTANCE])
    check._client = FakeClient(response=response)

    assert check._execute_query_raw('@Statistics:[MEMORY]') == [['first-row']]
