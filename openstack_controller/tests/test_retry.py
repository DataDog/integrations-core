# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import time

from . import common

from datadog_checks.openstack_controller import OpenStackControllerCheck
from datadog_checks.openstack_controller.retry import BackOffRetry


def test_retry(aggregator):
    instance = copy.deepcopy(common.MOCK_CONFIG["instances"][0])
    instance['tags'] = ['optional:tag1']
    init_config = copy.deepcopy(common.MOCK_CONFIG['init_config'])
    check = OpenStackControllerCheck('openstack', init_config, {}, instances=[instance])
    retry = BackOffRetry(check)
    assert retry.should_run(instance) is True
    assert retry.backoff["test_name"]['retries'] == 0
    # Make sure it is idempotent
    assert retry.should_run(instance) is True
    assert retry.backoff["test_name"]['retries'] == 0

    retry.do_backoff(instance)
    assert retry.should_run(instance) is False
    assert retry.backoff["test_name"]['retries'] == 1
    scheduled_1 = retry.backoff["test_name"]['scheduled']
    retry.do_backoff(instance)
    scheduled_2 = retry.backoff["test_name"]['scheduled']
    retry.do_backoff(instance)
    scheduled_3 = retry.backoff["test_name"]['scheduled']
    retry.do_backoff(instance)
    scheduled_4 = retry.backoff["test_name"]['scheduled']
    assert retry.backoff["test_name"]['retries'] == 4
    assert time.time() < scheduled_1 < scheduled_2 < scheduled_3 < scheduled_4

    for i in range(4):
        aggregator.assert_metric("openstack.backoff.retries", value=i+1, tags=['optional:tag1'])
        aggregator.assert_metric("openstack.backoff.interval", tags=['optional:tag1'])

    aggregator.assert_all_metrics_covered()
