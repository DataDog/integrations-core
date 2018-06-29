# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from requests.exceptions import SSLError
from datadog_checks.yarn import YarnCheck

from datadog_checks.yarn.yarn import (
    SERVICE_CHECK_NAME, YARN_QUEUE_METRICS, YARN_APP_METRICS
)

from .common import (
    YARN_CONFIG,
    YARN_CONFIG_EXCLUDING_APP,
    YARN_AUTH_CONFIG,
    YARN_APP_METRICS_TAGS,
    YARN_CLUSTER_METRICS_TAGS,
    YARN_NODE_METRICS_TAGS,
    YARN_ROOT_QUEUE_METRICS_TAGS,
    YARN_QUEUE_METRICS_TAGS,
    YARN_QUEUE_NOFOLLOW_METRICS_TAGS,
    YARN_CLUSTER_METRICS_VALUES,
    YARN_APP_METRICS_VALUES,
    YARN_NODE_METRICS_VALUES,
    YARN_ROOT_QUEUE_METRICS_VALUES,
    YARN_QUEUE_METRICS_VALUES,
    YARN_SSL_VERIFY_TRUE_CONFIG,
    YARN_SSL_VERIFY_FALSE_CONFIG,
    RM_ADDRESS,
    CUSTOM_TAGS,
)


def test_check(aggregator, mocked_request):
    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, {})

    # Run the check once
    yarn.check(YARN_CONFIG['instances'][0])

    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
    )

    # Check the YARN Cluster Metrics
    for metric, value in YARN_CLUSTER_METRICS_VALUES.iteritems():
        aggregator.assert_metric(metric, value=value, tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN App Metrics
    for metric, value in YARN_APP_METRICS_VALUES.iteritems():
        aggregator.assert_metric(metric, value=value, tags=YARN_APP_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Node Metrics
    for metric, value in YARN_NODE_METRICS_VALUES.iteritems():
        aggregator.assert_metric(metric, value=value, tags=YARN_NODE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Root Queue Metrics
    for metric, value in YARN_ROOT_QUEUE_METRICS_VALUES.iteritems():
        aggregator.assert_metric(metric, value=value, tags=YARN_ROOT_QUEUE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Custom Queue Metrics
    for metric, value in YARN_QUEUE_METRICS_VALUES.iteritems():
        aggregator.assert_metric(metric, value=value, tags=YARN_QUEUE_METRICS_TAGS + CUSTOM_TAGS, count=1)

    # Check the YARN Queue Metrics from excluded queues are absent
    for metric, value in YARN_QUEUE_METRICS.values():
        aggregator.assert_metric(metric, tags=YARN_QUEUE_NOFOLLOW_METRICS_TAGS + CUSTOM_TAGS, count=0)

    aggregator.assert_all_metrics_covered()


def test_check_excludes_app_metrics(aggregator, mocked_request):
    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, {})

    # Run the check once
    yarn.check(YARN_CONFIG_EXCLUDING_APP['instances'][0])

    # Check that the YARN App metrics is empty
    for metric, type in YARN_APP_METRICS.values():
        aggregator.assert_metric(metric, count=0)

    # Check that our service is up
    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
        count=3,
    )


def test_auth(aggregator, mocked_auth_request):
    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, {})

    # Run the check once
    yarn.check(YARN_AUTH_CONFIG['instances'][0])

    # Make sure check is working
    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
        count=4,
    )


def test_ssl_verification(aggregator, mocked_bad_cert_request):
    # Instantiate YarnCheck
    yarn = YarnCheck('yarn', {}, {})

    # Run the check on a config with a badly configured SSL certificate
    try:
        yarn.check(YARN_SSL_VERIFY_TRUE_CONFIG['instances'][0])
    except SSLError:
        aggregator.assert_service_check(
            SERVICE_CHECK_NAME,
            status=YarnCheck.CRITICAL,
            tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
            count=1
        )
        pass
    else:
        assert False, "Should have thrown an SSLError due to a badly configured certificate"

    # Run the check on the same configuration, but with verify=False. We shouldn't get an exception.
    yarn.check(YARN_SSL_VERIFY_FALSE_CONFIG['instances'][0])
    aggregator.assert_service_check(
        SERVICE_CHECK_NAME,
        status=YarnCheck.OK,
        tags=YARN_CLUSTER_METRICS_TAGS + CUSTOM_TAGS + ['url:{}'.format(RM_ADDRESS)],
        count=4,
    )
