# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import re

import pytest

from datadog_checks.base.utils.http_exceptions import HTTPRequestError, HTTPSSLError
from datadog_checks.yarn import YarnCheck
from datadog_checks.yarn.yarn import (
    APPLICATION_STATUS_SERVICE_CHECK,
    SERVICE_CHECK_NAME,
    YARN_APP_METRICS,
    YARN_QUEUE_METRICS,
)

from .common import (
    CUSTOM_TAGS,
    DEPRECATED_YARN_APP_METRICS_VALUES,
    RM_ADDRESS,
    TEST_PASSWORD,
    TEST_USERNAME,
    YARN_APP_METRICS_TAGS,
    YARN_APP_METRICS_VALUES,
    YARN_APPS_ALL_STATES,
    YARN_AUTH_CONFIG,
    YARN_CLUSTER_METRICS_TAGS,
    YARN_CLUSTER_METRICS_VALUES,
    YARN_CLUSTER_TAG,
    YARN_COLLECT_APPS_ALL_STATES_CONFIG,
    YARN_COLLECT_APPS_KILLED_INSTANCE_CONFIG,
    YARN_CONFIG,
    YARN_CONFIG_EXCLUDING_APP,
    YARN_CONFIG_SPLIT_APPLICATION_TAGS,
    YARN_CONFIG_STATUS_MAPPING,
    YARN_NODE_METRICS_TAGS,
    YARN_NODE_METRICS_VALUES,
    YARN_QUEUE_METRICS_TAGS,
    YARN_QUEUE_METRICS_VALUES,
    YARN_QUEUE_NOFOLLOW_METRICS_TAGS,
    YARN_ROOT_QUEUE_METRICS_TAGS,
    YARN_ROOT_QUEUE_METRICS_VALUES,
    YARN_SSL_VERIFY_FALSE_CONFIG,
    YARN_SSL_VERIFY_TRUE_CONFIG,
    YARN_SUBQUEUE_METRICS_TAGS,
    YARN_SUBQUEUE_METRICS_VALUES,
)

EXPECTED_TAGS = YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS


def test_check(aggregator, mocked_request):
    instance = YARN_CONFIG['instances'][0]

    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, [instance])

    # Run the check once
    yarn.check(instance)

    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=EXPECTED_TAGS + ['url:{}'.format(RM_ADDRESS)],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:word count', 'state:RUNNING'] + EXPECTED_TAGS,
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.CRITICAL,
        tags=['app_queue:default', 'app_name:dead app', 'state:KILLED'] + EXPECTED_TAGS,
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:new app', 'state:NEW'] + EXPECTED_TAGS,
    )

    # Check the YARN Cluster Metrics
    for metric, value in YARN_CLUSTER_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=EXPECTED_TAGS, count=1)

    # Check the YARN App Metrics
    for metric, value in YARN_APP_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=YARN_APP_METRICS_TAGS + CUSTOM_TAGS, count=1)
    for metric, value in DEPRECATED_YARN_APP_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=YARN_APP_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Node Metrics
    for metric, value in YARN_NODE_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=YARN_NODE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Root Queue Metrics
    for metric, value in YARN_ROOT_QUEUE_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=YARN_ROOT_QUEUE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Custom Queue Metrics
    for metric, value in YARN_QUEUE_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=YARN_QUEUE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Queue Metrics from excluded queues are absent
    for metric, _ in YARN_QUEUE_METRICS.values():
        aggregator.assert_metric(metric, tags=YARN_QUEUE_NOFOLLOW_METRICS_TAGS + CUSTOM_TAGS, count=0)

    # Check the YARN Subqueue Metrics
    for metric, value in YARN_SUBQUEUE_METRICS_VALUES.items():
        aggregator.assert_metric(metric, value=value, tags=YARN_SUBQUEUE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    aggregator.assert_all_metrics_covered()


def test_check_mapping(aggregator, mocked_request):
    instance = YARN_CONFIG_STATUS_MAPPING['instances'][0]

    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, [instance])

    # Run the check once
    yarn.check(instance)

    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=EXPECTED_TAGS + ['url:{}'.format(RM_ADDRESS)],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:word count', 'state:RUNNING'] + EXPECTED_TAGS,
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.WARNING,
        tags=['app_queue:default', 'app_name:dead app', 'state:KILLED'] + EXPECTED_TAGS,
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:new app', 'state:NEW'] + EXPECTED_TAGS,
    )


def test_check_excludes_app_metrics(aggregator, mocked_request):
    instance = YARN_CONFIG_EXCLUDING_APP['instances'][0]

    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, [instance])

    # Run the check once
    yarn.check(instance)

    # Check that the YARN App metrics is empty
    for metric, _ in YARN_APP_METRICS.values():
        aggregator.assert_metric(metric, count=0)

    # Check that our service is up
    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=EXPECTED_TAGS + ['url:{}'.format(RM_ADDRESS)],
        count=3,
    )


def test_custom_mapping(aggregator, mocked_request):
    instance = copy.deepcopy(YARN_CONFIG['instances'][0])
    instance['application_status_mapping'] = {'KILLED': 'WARNING', 'RUNNING': 'OK'}

    yarn = YarnCheck('yarn', {}, [instance])

    # Run the check once
    yarn.check(instance)

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:word count', 'state:RUNNING'] + EXPECTED_TAGS,
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.WARNING,
        tags=['app_queue:default', 'app_name:dead app', 'state:KILLED'] + EXPECTED_TAGS,
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.UNKNOWN,
        tags=['app_queue:default', 'app_name:new app', 'state:NEW'] + EXPECTED_TAGS,
    )


def test_check_splits_yarn_application_tags(aggregator, mocked_request):
    instance = YARN_CONFIG_SPLIT_APPLICATION_TAGS['instances'][0]

    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, [instance])

    # Run the check once
    yarn.check(instance)

    # Check that the YARN application tags have been split for properly formatted tags
    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:word count', 'app_key1:value1', 'app_key2:value2', 'state:RUNNING']
        + EXPECTED_TAGS,
    )

    # And check that the YARN application tags have not been split for other tags
    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.WARNING,
        tags=['app_queue:default', 'app_name:dead app', 'app_tag1', 'app_tag2', 'state:KILLED'] + EXPECTED_TAGS,
    )


def test_disable_legacy_cluster_tag(aggregator, mocked_request):
    instance = YARN_CONFIG_SPLIT_APPLICATION_TAGS['instances'][0]
    instance['disable_legacy_cluster_tag'] = True

    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, [instance])

    # Run the check once
    yarn.check(instance)
    # Check that the YARN application tags have been split for properly formatted tags without cluster_name tag
    expected_tags = CUSTOM_TAGS
    expected_tags.append(YARN_CLUSTER_TAG)
    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:word count', 'app_key1:value1', 'app_key2:value2', 'state:RUNNING']
        + expected_tags,
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.WARNING,
        tags=['app_queue:default', 'app_name:dead app', 'app_tag1', 'app_tag2', 'state:KILLED'] + expected_tags,
    )


def test_auth():
    instance = YARN_AUTH_CONFIG['instances'][0]
    yarn = YarnCheck('yarn', {}, [instance])

    assert yarn.http.options['auth'] == (TEST_USERNAME, TEST_PASSWORD)


@pytest.mark.parametrize(
    ('config', 'expected_tls_verify'),
    [
        pytest.param(YARN_SSL_VERIFY_TRUE_CONFIG, True, id='enabled'),
        pytest.param(YARN_SSL_VERIFY_FALSE_CONFIG, False, id='disabled'),
    ],
)
def test_ssl_verification_configuration(config, expected_tls_verify):
    instance = config['instances'][0]
    yarn = YarnCheck('yarn', {}, [instance])

    assert yarn.http.options['verify'] is expected_tls_verify


def test_ssl_verification_error(aggregator, mock_http):
    mock_http.get.side_effect = HTTPSSLError("certificate verification failed")
    instance = YARN_SSL_VERIFY_TRUE_CONFIG['instances'][0]
    yarn = YarnCheck('yarn', {}, [instance])

    with pytest.raises(HTTPSSLError, match="certificate verification failed"):
        yarn.check(instance)

    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.CRITICAL,
        tags=EXPECTED_TAGS + ['url:{}'.format(RM_ADDRESS)],
        count=1,
    )


def test_malformed_header_still_reports_critical(aggregator, mock_http):
    """A server-sent malformed header must still emit yarn.can_connect.

    urllib3 raises InvalidHeader for a multi-valued Content-Length and requests re-raises it as
    its own InvalidHeader, which subclasses ValueError. The agnostic translator has no equivalent
    subtype and collapses it into a bare HTTPRequestError, so the last arm has to name that type.
    """
    message = 'Content-Length contained multiple unmatching values'
    mock_http.get.side_effect = HTTPRequestError(message)
    instance = YARN_SSL_VERIFY_TRUE_CONFIG['instances'][0]
    yarn = YarnCheck('yarn', {}, [instance])

    with pytest.raises(HTTPRequestError, match=message):
        yarn.check(instance)

    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.CRITICAL,
        tags=EXPECTED_TAGS + ['url:{}'.format(RM_ADDRESS)],
        count=1,
    )
    # Merge base reported the bare error text here, not the "Request failed" prefix that the
    # status/connection arm uses. Pin it so the fix stays on the last arm.
    assert aggregator.service_checks(SERVICE_CHECK_NAME)[0].message == message


def test_collect_apps_all_states(dd_run_check, aggregator, mocked_request):
    instance = YARN_COLLECT_APPS_ALL_STATES_CONFIG['instances'][0]
    yarn = YarnCheck('yarn', {}, [instance])

    dd_run_check(yarn)

    for app in YARN_APPS_ALL_STATES:
        for metric, value in app['metric_values'].items():
            aggregator.assert_metric(metric, value=value, tags=app['tags'] + EXPECTED_TAGS, count=1)


@pytest.mark.parametrize(
    'config',
    [
        pytest.param(['RUNNING', 'NEW'], id='RUNNING and NEW'),
        pytest.param(['NEW'], id='NEW only'),
        pytest.param(['NEW', 'KILLED'], id='NEW and KILLED'),
        pytest.param(['RUNNING', 'NEW', 'KILLED'], id='RUNNING, NEW, and KILLED'),
    ],
)
def test_collect_apps_states_list(dd_run_check, aggregator, mocked_request, config):
    instance = YARN_CONFIG['instances'][0]
    instance['collect_apps_states_list'] = config
    state_tags = ['state:{}'.format(state) for state in config]
    yarn = YarnCheck('yarn', {}, [instance])
    dd_run_check(yarn)
    state_tag_re = re.compile(r'state:.*')

    for app in YARN_APPS_ALL_STATES:
        for metric, value in app['metric_values'].items():
            m = re.search(state_tag_re, app['tags'][2])
            if m:
                state_tag = m.group(0)
                if state_tag in state_tags:
                    aggregator.assert_metric(metric, value=value, tags=app['tags'] + EXPECTED_TAGS, count=1)
                else:
                    aggregator.assert_metric(metric, tags=app['tags'] + EXPECTED_TAGS, count=0)


def test_collect_apps_killed_instance_state(dd_run_check, aggregator, mocked_request):
    instance = YARN_COLLECT_APPS_KILLED_INSTANCE_CONFIG['instances'][0]
    yarn = YarnCheck('yarn', YARN_COLLECT_APPS_KILLED_INSTANCE_CONFIG['init_config'], [instance])

    dd_run_check(yarn)

    for app in YARN_APPS_ALL_STATES:
        for metric, value in app['metric_values'].items():
            if app['tags'] == "KILLED":
                aggregator.assert_metric(metric, value=value, tags=app['tags'] + EXPECTED_TAGS, count=1)
            else:
                aggregator.assert_metric(metric, value=value, tags=app['tags'] + EXPECTED_TAGS, count=0)
