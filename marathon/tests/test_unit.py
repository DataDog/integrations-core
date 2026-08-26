# (C) Datadog, Inc. 2018-present
# (C)  graemej <graeme.johnson@jadedpixel.com> 2014
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy

import mock
import pytest
import requests

from datadog_checks.base import AgentCheck
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.marathon import Marathon

from .common import INSTANCE_INTEGRATION

pytestmark = pytest.mark.unit


def test_get_app_tags(check):
    app = {'id': 'my_app_id', 'version': 'my_app_version', 'labels': {'label_foo': 'foo_value'}}

    # call with default params
    assert check.get_app_tags(app) == ['app_id:my_app_id', 'version:my_app_version']

    # call with tags
    assert check.get_app_tags(app, ['foo:bar']) == ['app_id:my_app_id', 'version:my_app_version', 'foo:bar']

    # call with labels (one label doesn't exist in app)
    assert check.get_app_tags(app, ['foo:bar'], ['label_foo', 'label_bar']) == [
        'app_id:my_app_id',
        'version:my_app_version',
        'foo:bar',
        'label_foo:foo_value',
    ]

    # call with empty values
    app = {'id': '', 'version': ''}
    assert check.get_app_tags(app) == ['app_id:', 'version:']


def test_process_apps_ko(check, aggregator):
    """
    If the check can't hit the Marathon master Url, no metric should be
    collected
    """
    check.get_apps_json = mock.MagicMock(return_value=None)
    check.process_apps('url', 'acs_url', [], [], None)
    assert len(aggregator.metric_names) == 0


def test_process_apps(check, aggregator):
    check.get_apps_json = mock.MagicMock(
        return_value={
            'apps': [
                {'id': '/', 'version': '', 'backoffSeconds': 99},
                {'id': '/', 'version': '', 'backoffSeconds': 101},
            ]
        }
    )

    check.process_apps('url', 'acs_url', [], [], None)
    aggregator.assert_metric('marathon.apps', value=2, count=1)
    aggregator.assert_metric('marathon.backoffSeconds', value=99, count=1, tags=['app_id:/', 'version:'])
    aggregator.assert_metric('marathon.backoffSeconds', value=101, count=1, tags=['app_id:/', 'version:'])


def test_get_instance_config(check):
    # test mandatory
    instance = {}
    with pytest.raises(Exception) as e:
        check.get_instance_config(instance)
        assert str(e) == 'Marathon instance missing "url" value.'

    # test defaults
    instance = {'url': 'http://foo'}
    url, acs_url, group, tags, label_tags = check.get_instance_config(instance)
    assert url == 'http://foo'
    assert acs_url is None
    assert group is None
    assert tags == []
    assert label_tags == []

    # test misc
    instance = {'url': 'http://foo', 'disable_ssl_validation': True, 'tags': ['foo:bar'], 'label_tags': ['label_foo']}
    _, acs_url, _, tags, label_tags = check.get_instance_config(instance)
    assert tags == ['foo:bar']
    assert label_tags == ['label_foo']


@pytest.mark.parametrize(
    'test_case, init_config, extra_config, expected_http_kwargs',
    [
        (
            "new config",
            {},
            {'timeout': 5, 'username': 'foo', 'password': 'bar', 'tls_verify': False},
            {'timeout': 5, 'auth': ('foo', 'bar'), 'verify': False},
        ),
        ("connect_timeout", {'default_timeout': 5}, {'connect_timeout': 2}, {'timeout': (5.0, 2.0)}),
        ("read_timeout", {}, {'timeout': 7, 'read_timeout': 3}, {'timeout': (3.0, 7.0)}),
        (
            "legacy config",
            {'default_timeout': 3},
            {'user': 'foo', 'password': 'bar', 'disable_ssl_validation': True},
            {'timeout': 3, 'auth': ('foo', 'bar'), 'verify': False},
        ),
        ("default config", {}, {}, {'verify': True}),
    ],
)
def test_config(test_case, init_config, extra_config, expected_http_kwargs):
    instance = deepcopy(INSTANCE_INTEGRATION)
    instance.update(extra_config)
    check = Marathon('marathon', init_config, instances=[instance])

    r = mock.MagicMock()
    with mock.patch('datadog_checks.base.utils.http.requests.Session', return_value=r):
        r.get.return_value = mock.MagicMock(status_code=200)

        check.check(instance)

        http_wargs = {
            'auth': mock.ANY,
            'cert': mock.ANY,
            'headers': mock.ANY,
            'proxies': mock.ANY,
            'timeout': mock.ANY,
            'verify': mock.ANY,
            'allow_redirects': mock.ANY,
        }
        http_wargs.update(expected_http_kwargs)
        r.get.assert_called_with('http://localhost:8080/v2/queue', **http_wargs)


def test_default_timeout_used_when_not_configured(check):
    # Kills the core/NumberReplacer mutants at marathon.py:13 (DEFAULT_TIMEOUT 5 -> 6/4).
    assert check.http.options['timeout'] == 5


def test_auth_body_built_from_http_auth_tuple():
    # Kills the core/NumberReplacer mutants at marathon.py:67 (auth tuple index swaps in _auth_body).
    instance = {'url': 'http://foo', 'username': 'foouser', 'password': 'barpass'}
    check = Marathon('marathon', {}, [instance])
    assert check._auth_body == {'uid': 'foouser', 'password': 'barpass'}


def test_check_logs_and_reraises_on_invalid_instance_config(check, caplog):
    # Kills the core/ExceptionReplacer mutant at marathon.py:72 (except Exception -> except CosmicRayTestingException).
    with pytest.raises(Exception, match=r'Marathon instance missing "url" value\.'):
        check.check({})
    assert 'Invalid instance configuration.' in caplog.text


def test_refresh_acs_token_defaults_tags_and_reports_http_error(check, aggregator):
    resp = mock.MagicMock(status_code=400)
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError()

    # Kills the core/ReplaceComparisonOperator_Is_IsNot, AddNot (tags defaulting to []), ExceptionReplacer
    # (HTTPError catch), and ReplaceBinaryOperator_Add_* mutants (tags/message concatenation) at
    # marathon.py:82,91,96,98.
    with mock.patch.object(RequestsWrapper, 'post', return_value=resp):
        with pytest.raises(Exception, match=r'^Got 400 when hitting http://acs$'):
            check.refresh_acs_token('http://acs')

    aggregator.assert_service_check(
        check.SERVICE_CHECK_NAME,
        status=AgentCheck.CRITICAL,
        tags=['url:http://acs'],
        count=1,
        message=r'acs auth url http://acs returned a status of 400',
    )


def test_refresh_acs_token_posts_without_ssl_verification(check):
    resp = mock.MagicMock(status_code=200)
    resp.json.return_value = {'token': 'xyz'}

    # Kills the core/ReplaceFalseWithTrue mutant at marathon.py:86 (verify=False -> verify=True).
    with mock.patch.object(RequestsWrapper, 'post', return_value=resp) as post_mock:
        check.refresh_acs_token('http://acs')
    _, kwargs = post_mock.call_args
    assert kwargs['verify'] is False


def test_get_json_defaults_tags_on_success(check, aggregator):
    resp = mock.MagicMock(status_code=200)
    resp.json.return_value = {'ok': True}

    # Kills the core/ReplaceComparisonOperator_Is_IsNot and AddNot mutants at marathon.py:101
    # (tags defaulting to [] in get_json).
    with mock.patch.object(RequestsWrapper, 'get', return_value=resp):
        result = check.get_json('http://foo', None)
    assert result == {'ok': True}
    aggregator.assert_service_check(check.SERVICE_CHECK_NAME, status=AgentCheck.OK, tags=['url:http://foo'], count=1)


def test_get_json_skips_acs_token_refresh_without_acs_url(check):
    resp = mock.MagicMock(status_code=200)
    resp.json.return_value = {'ok': True}

    with mock.patch.object(RequestsWrapper, 'get', return_value=resp), mock.patch.object(
        RequestsWrapper, 'post'
    ) as post_mock:
        # Kills the core/AddNot mutant at marathon.py:104 (if acs_url: -> if not acs_url:).
        check.get_json('http://foo', None, tags=[])
        assert post_mock.call_count == 0
    assert 'authorization' not in check.http.options['headers']


def test_get_json_refreshes_acs_token_when_missing(check):
    post_resp = mock.MagicMock(status_code=200)
    post_resp.json.return_value = {'token': 'tok1'}
    get_resp = mock.MagicMock(status_code=200)
    get_resp.json.return_value = {'ok': True}

    with mock.patch.object(RequestsWrapper, 'post', return_value=post_resp) as post_mock, mock.patch.object(
        RequestsWrapper, 'get', return_value=get_resp
    ):
        # Kills the core/ReplaceUnaryOperator_Delete_Not and AddNot mutants at marathon.py:106
        # (if not self.ACS_TOKEN: check).
        check.get_json('http://foo', 'http://acs', tags=[])
        assert post_mock.call_count == 1
    assert check.http.options['headers']['authorization'] == 'token=tok1'
    assert check.ACS_TOKEN == 'tok1'


def test_get_json_retries_after_401_with_acs_url(check):
    post_resp = mock.MagicMock(status_code=200)
    post_resp.json.return_value = {'token': 'tok2'}
    resp_401 = mock.MagicMock(status_code=401)
    resp_ok = mock.MagicMock(status_code=200)
    resp_ok.json.return_value = {'ok': True}

    with mock.patch.object(RequestsWrapper, 'post', return_value=post_resp), mock.patch.object(
        RequestsWrapper, 'get', side_effect=[resp_401, resp_ok]
    ) as get_mock:
        # Kills the core/ReplaceComparisonOperator_Eq_* and NumberReplacer mutants at marathon.py:113
        # (r.status_code == 401 check).
        result = check.get_json('http://foo', 'http://acs', tags=[])
        assert result == {'ok': True}
        assert get_mock.call_count == 2


def test_get_json_does_not_retry_when_status_is_not_401(check):
    check.ACS_TOKEN = 'existing-token'
    resp_ok = mock.MagicMock(status_code=200)
    resp_ok.json.return_value = {'ok': True}

    with mock.patch.object(RequestsWrapper, 'get', return_value=resp_ok) as get_mock:
        # Kills the core/ReplaceAndWithOr mutant at marathon.py:113 (status_code == 401 and acs_url).
        check.get_json('http://foo', 'http://acs', tags=[])
        assert get_mock.call_count == 1


def test_get_json_does_not_retry_when_status_exceeds_401(check):
    check.ACS_TOKEN = 'existing-token'
    resp = mock.MagicMock(status_code=500)

    with mock.patch.object(RequestsWrapper, 'get', return_value=resp) as get_mock:
        # Kills the core/ReplaceComparisonOperator_Eq_GtE mutant at marathon.py:113 (status_code == 401 -> >= 401).
        check.get_json('http://foo', 'http://acs', tags=[])
        assert get_mock.call_count == 1


def test_get_json_timeout_reports_configured_timeout_value(aggregator):
    instance = {'url': 'http://foo', 'read_timeout': 3, 'connect_timeout': 7}
    check = Marathon('marathon', {}, [instance])

    # Kills the core/ExceptionReplacer (Timeout catch), NumberReplacer (timeout tuple index), and
    # ReplaceBinaryOperator_Add_* mutants (tags concatenation) at marathon.py:117,122,123.
    with mock.patch.object(RequestsWrapper, 'get', side_effect=requests.exceptions.Timeout()):
        with pytest.raises(Exception, match=r'^Timeout when hitting http://foo$'):
            check.get_json('http://foo', None, tags=['t1'])

    aggregator.assert_service_check(
        check.SERVICE_CHECK_NAME,
        status=AgentCheck.CRITICAL,
        tags=['url:http://foo', 't1'],
        count=1,
        message=r'http://foo timed out after 3\.0 seconds\.',
    )


def test_get_json_http_error_reports_status_and_tags(check, aggregator):
    resp = mock.MagicMock(status_code=500)
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError()

    # Kills the core/ExceptionReplacer (HTTPError catch) and ReplaceBinaryOperator_Add_* mutants
    # (tags concatenation) at marathon.py:127,132.
    with mock.patch.object(RequestsWrapper, 'get', return_value=resp):
        with pytest.raises(Exception, match=r'^Got 500 when hitting http://foo/apps$'):
            check.get_json('http://foo/apps', None, tags=['t2'])

    aggregator.assert_service_check(
        check.SERVICE_CHECK_NAME,
        status=AgentCheck.CRITICAL,
        tags=['url:http://foo/apps', 't2'],
        count=1,
        message=r'http://foo/apps returned a status of 500',
    )


def test_get_json_connection_error_reports_tags(check, aggregator):
    # Kills the core/ExceptionReplacer (ConnectionError catch) and ReplaceBinaryOperator_Add_* mutants
    # (tags concatenation) at marathon.py:136,141.
    with mock.patch.object(RequestsWrapper, 'get', side_effect=requests.exceptions.ConnectionError()):
        with pytest.raises(Exception, match=r'^Connection refused when hitting http://foo/apps$'):
            check.get_json('http://foo/apps', None, tags=['t3'])

    aggregator.assert_service_check(
        check.SERVICE_CHECK_NAME,
        status=AgentCheck.CRITICAL,
        tags=['url:http://foo/apps', 't3'],
        count=1,
        message=r'http://foo/apps Connection Refused\.',
    )


def test_get_apps_json_uses_apps_endpoint_when_group_is_none(check):
    check.apps_response = None
    check.get_json = mock.MagicMock(return_value={'apps': []})

    # Kills the core/ReplaceComparisonOperator_Is_IsNot and AddNot mutants at marathon.py:173
    # (if group is None: branch selection).
    check.get_apps_json('http://foo/', None, [], None)
    check.get_json.assert_called_once_with('http://foo/v2/apps?embed=apps.counts', None, [])


def test_get_apps_json_uses_group_endpoint_when_group_set(check):
    check.apps_response = None
    check.get_json = mock.MagicMock(return_value={'apps': []})

    # Kills the core/ReplaceBinaryOperator_Add_* mutants at marathon.py:179 (group path string concatenation).
    check.get_apps_json('http://foo/', None, [], 'mygroup')
    expected_path = 'http://foo/v2/groups/mygroup?embed=group.groups&embed=group.apps&embed=group.apps.counts'
    check.get_json.assert_called_once_with(expected_path, None, [])


def test_process_deployments_skips_gauge_when_response_none(check, aggregator):
    check.get_json = mock.MagicMock(return_value=None)

    # Kills the core/ReplaceComparisonOperator_IsNot_Is and AddNot mutants at marathon.py:200
    # (if response is not None: check).
    check.process_deployments('http://foo', None, tags=['t'])
    aggregator.assert_metric('marathon.deployments', count=0)


def test_process_queues_returns_early_when_response_none(check, aggregator):
    check.get_json = mock.MagicMock(return_value=None)

    # Kills the core/ReplaceComparisonOperator_Is_IsNot and AddNot mutants at marathon.py:205
    # (if response is None: early-return check).
    check.process_queues('http://foo', None, tags=[], label_tags=[], group=None)
    assert aggregator.metric_names == []


def test_process_queues_emits_all_queue_metrics(check, aggregator):
    check.apps_response = None
    queue_entry = {
        'app': {'id': '/app1', 'version': 'v1'},
        'count': 3,
        'delay': {'timeLeftSeconds': 12},
        'processedOffersSummary': {
            'processedOffersCount': 5,
            'unusedOffersCount': 2,
            'rejectSummaryLastOffers': [{'reason': 'r1', 'declined': 1, 'processed': 4}],
            'rejectSummaryLaunchAttempt': [{'reason': 'r2', 'declined': 2, 'processed': 6}],
        },
    }

    def side_effect(url, acs_url, tags):
        if 'v2/queue' in url:
            return {'queue': [queue_entry]}
        elif 'v2/apps' in url:
            return {'apps': [{'id': '/app1', 'version': 'v1'}]}
        raise AssertionError('unexpected url: {}'.format(url))

    check.get_json = mock.MagicMock(side_effect=side_effect)
    check.process_queues('http://foo/', None, tags=[], label_tags=[], group=None)

    q_tags = ['app_id:/app1', 'version:v1']
    # Kills the core/ZeroIterationForLoop, AddNot, and ReplaceBinaryOperator_Add_* mutants at
    # marathon.py:213,218,219,220,224,225,229,230,231,242 (queue/QUEUE_METRICS traversal and summary tags).
    aggregator.assert_metric('marathon.queue.size', value=1)
    aggregator.assert_metric('marathon.queue.count', value=3, tags=q_tags)
    aggregator.assert_metric('marathon.queue.delay', value=12, tags=q_tags)
    aggregator.assert_metric('marathon.queue.offers.processed', value=5, tags=q_tags)
    aggregator.assert_metric('marathon.queue.offers.unused', value=2, tags=q_tags)
    aggregator.assert_metric('marathon.queue.offers.reject.last', value=1, tags=q_tags + ['reason:r1', 'status:declined'])
    aggregator.assert_metric('marathon.queue.offers.reject.last', value=4, tags=q_tags + ['reason:r1', 'status:processed'])
    aggregator.assert_metric(
        'marathon.queue.offers.reject.launch', value=2, tags=q_tags + ['reason:r2', 'status:declined']
    )
    aggregator.assert_metric(
        'marathon.queue.offers.reject.launch', value=6, tags=q_tags + ['reason:r2', 'status:processed']
    )


def test_process_queues_swallows_lookup_and_type_errors(check, aggregator):
    check.apps_response = None
    queue_entry = {
        'app': {'id': '/appX', 'version': 'vX'},
        'count': {},  # float({}) raises TypeError in the scalar sub-metric branch
        'delay': {},  # missing 'timeLeftSeconds' raises KeyError in the scalar sub-metric branch
        'processedOffersSummary': {
            'processedOffersCount': 7,
            # 'unusedOffersCount' intentionally missing raises KeyError in the list sub-metric branch
            'rejectSummaryLastOffers': [{'reason': 'r1', 'declined': 1, 'processed': 2}],
            'rejectSummaryLaunchAttempt': 999,  # not iterable, raises TypeError in the list sub-metric branch
        },
    }

    def side_effect(url, acs_url, tags):
        if 'v2/queue' in url:
            return {'queue': [queue_entry]}
        elif 'v2/apps' in url:
            return {'apps': [{'id': '/appX', 'version': 'vX'}]}
        raise AssertionError('unexpected url: {}'.format(url))

    check.get_json = mock.MagicMock(side_effect=side_effect)
    # Kills the core/ExceptionReplacer mutants at marathon.py:235,245 (KeyError/TypeError swallowed per sub-metric).
    check.process_queues('http://foo/', None, tags=[], label_tags=[], group=None)

    q_tags = ['app_id:/appX', 'version:vX']
    aggregator.assert_metric('marathon.queue.offers.processed', value=7, tags=q_tags)
    aggregator.assert_metric('marathon.queue.offers.reject.last', value=1, tags=q_tags + ['reason:r1', 'status:declined'])
    aggregator.assert_metric('marathon.queue.count', count=0)
    aggregator.assert_metric('marathon.queue.delay', count=0)
    aggregator.assert_metric('marathon.queue.offers.unused', count=0)
    aggregator.assert_metric('marathon.queue.offers.reject.launch', count=0)


def test_ensure_queue_count_zero_for_unqueued_apps_only(check, aggregator):
    check.get_apps_json = mock.MagicMock(
        return_value={'apps': [{'id': '/queued', 'version': 'v1'}, {'id': '/unqueued', 'version': 'v2'}]}
    )

    # Kills the core/ZeroIterationForLoop, AddNot, and NumberReplacer mutants at marathon.py:279,280,282
    # (zero-count metric emitted only for apps missing from the queued set).
    check.ensure_queue_count({'/queued'}, 'http://foo', None, tags=[], label_tags=[], group=None)
    aggregator.assert_metric('marathon.queue.count', value=0, count=1, tags=['app_id:/unqueued', 'version:v2'])
    aggregator.assert_metric('marathon.queue.count', tags=['app_id:/queued', 'version:v1'], count=0)
