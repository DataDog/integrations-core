# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy
import os

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
    YARN_AUTH_CONFIG,
    YARN_CLUSTER_METRICS_TAGS,
    YARN_CLUSTER_METRICS_VALUES,
    YARN_CONFIG,
    YARN_CONFIG_EXCLUDING_APP,
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
)


def test_check(aggregator, mocked_request):
    instance = YARN_CONFIG['instances'][0]

    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, [instance])

    # Run the check once
    yarn.check(instance)

    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:word count', 'optional:tag1', 'cluster_name:SparkCluster'],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.CRITICAL,
        tags=['app_queue:default', 'app_name:dead app', 'optional:tag1', 'cluster_name:SparkCluster'],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:new app', 'optional:tag1', 'cluster_name:SparkCluster'],
    )

    # Check the YARN Cluster Metrics
    for metric, value in iteritems(YARN_CLUSTER_METRICS_VALUES):
        aggregator.assert_metric(metric, value=value, tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS, count=1)

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
        tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:word count', 'optional:tag1', 'cluster_name:SparkCluster'],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.WARNING,
        tags=['app_queue:default', 'app_name:dead app', 'optional:tag1', 'cluster_name:SparkCluster'],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.OK,
        tags=['app_queue:default', 'app_name:new app', 'optional:tag1', 'cluster_name:SparkCluster'],
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
        tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
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
        tags=['app_queue:default', 'app_name:word count', 'optional:tag1', 'cluster_name:SparkCluster'],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.WARNING,
        tags=['app_queue:default', 'app_name:dead app', 'optional:tag1', 'cluster_name:SparkCluster'],
    )

    aggregator.assert_service_check(
        APPLICATION_STATUS_SERVICE_CHECK,
        status=YarnCheck.UNKNOWN,
        tags=['app_queue:default', 'app_name:new app', 'optional:tag1', 'cluster_name:SparkCluster'],
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
        tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
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
            tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
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
        tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
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
