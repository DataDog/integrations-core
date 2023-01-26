# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os
import re

import pytest
from requests.exceptions import SSLError
from six import iteritems

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
    YARN_APP_METRICS_TAGS,
    YARN_APP_METRICS_VALUES,
    YARN_APPS_ALL_STATES,
    YARN_AUTH_CONFIG,
    YARN_CLUSTER_METRICS_TAGS,
    YARN_CLUSTER_METRICS_VALUES,
    YARN_CLUSTER_TAG,
    YARN_COLLECT_APPS_ALL_STATES_CONFIG,
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
    for metric, value in iteritems(YARN_CLUSTER_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=EXPECTED_TAGS, count=1)

    # Check the YARN App Metrics
    for metric, value in iteritems(YARN_APP_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=YARN_APP_METRICS_TAGS + CUSTOM_TAGS, count=1)
    for metric, value in iteritems(DEPRECATED_YARN_APP_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=YARN_APP_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Node Metrics
    for metric, value in iteritems(YARN_NODE_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=YARN_NODE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Root Queue Metrics
    for metric, value in iteritems(YARN_ROOT_QUEUE_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=YARN_ROOT_QUEUE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Custom Queue Metrics
    for metric, value in iteritems(YARN_QUEUE_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=YARN_QUEUE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Queue Metrics from excluded queues are absent
    for metric, _ in YARN_QUEUE_METRICS.values():
        aggregator.assert_metric(metric, tags=YARN_QUEUE_NOFOLLOW_METRICS_TAGS + CUSTOM_TAGS, count=0)

    # Check the YARN Subqueue Metrics
    for metric, value in iteritems(YARN_SUBQUEUE_METRICS_VALUES):
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


def test_auth(aggregator, mocked_auth_request):
    instance = YARN_AUTH_CONFIG['instances'][0]

    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, [instance])

    # Run the check once
    yarn.check(instance)

    # Make sure check is working
    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=EXPECTED_TAGS + ['url:{}'.format(RM_ADDRESS)],
        count=4,
    )


def test_ssl_verification(aggregator, mocked_bad_cert_request):
    instance = YARN_SSL_VERIFY_TRUE_CONFIG['instances'][0]

    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, [instance])

    # Run the check on a config with a badly configured SSL certificate
    try:
        yarn.check(instance)
    except SSLError:
        aggregator.assert_service_check(
            SERVICE_CHECK_NAME,
            status=YarnCheck.CRITICAL,
            tags=EXPECTED_TAGS + ['url:{}'.format(RM_ADDRESS)],
            count=1,
        )
        pass
    else:
        raise AssertionError('Should have thrown an SSLError due to a badly configured certificate')

    # Run the check on the same configuration, but with verify=False. We shouldn't get an exception.
    instance = YARN_SSL_VERIFY_FALSE_CONFIG['instances'][0]
    yarn = YarnCheck('yarn', {}, [instance])
    yarn.check(instance)
    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=EXPECTED_TAGS + ['url:{}'.format(RM_ADDRESS)],
        count=4,
    )


def test_metadata(aggregator, instance, datadog_agent):
    check = YarnCheck("yarn", {}, [instance])
    check.check_id = "test:123"

    check.check(instance)

    raw_version = os.getenv("YARN_VERSION")

    major, minor, patch = raw_version.split(".")

    version_metadata = {
        "version.scheme": "semver",
        "version.major": major,
        "version.minor": minor,
        "version.patch": patch,
        "version.raw": raw_version,
    }

    datadog_agent.assert_metadata("test:123", version_metadata)


def test_collect_apps_all_states(dd_run_check, aggregator, mocked_request):
    instance = YARN_COLLECT_APPS_ALL_STATES_CONFIG['instances'][0]
    yarn = YarnCheck('yarn', {}, [instance])

    dd_run_check(yarn)

    for app in YARN_APPS_ALL_STATES:
        for metric, value in iteritems(app['metric_values']):
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
        for metric, value in iteritems(app['metric_values']):
            m = re.search(state_tag_re, app['tags'][2])
            if m:
                state_tag = m.group(0)
                if state_tag in state_tags:
                    aggregator.assert_metric(metric, value=value, tags=app['tags'] + EXPECTED_TAGS, count=1)
                else:
                    aggregator.assert_metric(metric, tags=app['tags'] + EXPECTED_TAGS, count=0)
