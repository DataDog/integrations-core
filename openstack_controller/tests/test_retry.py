# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import time
from . import common

from datadog_checks.openstack_controller.retry import BackOffRetry


def test_retry():
    instance = copy.deepcopy(common.MOCK_CONFIG["instances"][0])
    instance['tags'] = ['optional:tag1']
    retry = BackOffRetry()
    assert retry.should_run('test_name') is True
    assert retry.backoff["test_name"]['retries'] == 0
    # Make sure it is idempotent
    assert retry.should_run('test_name') is True
    assert retry.backoff["test_name"]['retries'] == 0

    retry.do_backoff('test_name')
    assert retry.should_run('test_name') is False
    assert retry.backoff["test_name"]['retries'] == 1
    scheduled_1 = retry.backoff["test_name"]['scheduled']
    retry.do_backoff('test_name')
    scheduled_2 = retry.backoff["test_name"]['scheduled']
    retry.do_backoff('test_name')
    scheduled_3 = retry.backoff["test_name"]['scheduled']
    retry.do_backoff('test_name')
    scheduled_4 = retry.backoff["test_name"]['scheduled']
    assert retry.backoff["test_name"]['retries'] == 4
    assert time.time() < scheduled_1 < scheduled_2 < scheduled_3 < scheduled_4
