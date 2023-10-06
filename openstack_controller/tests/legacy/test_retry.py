# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import copy
import os
import time

import pytest

from datadog_checks.openstack_controller.legacy.retry import BackOffRetry

from . import common

pytestmark = [
    pytest.mark.unit,
    pytest.mark.skipif(
        os.environ.get('OPENSTACK_E2E_LEGACY') is None or os.environ.get('OPENSTACK_E2E_LEGACY') == 'false',
        reason='Legacy test',
    ),
]


def test_retry():
    instance = copy.deepcopy(common.MOCK_CONFIG["instances"][0])
    instance['tags'] = ['optional:tag1']
    retry = BackOffRetry()
    assert retry.should_run() is True
    assert retry.backoff['retries'] == 0
    # Make sure it is idempotent
    assert retry.should_run() is True
    assert retry.backoff['retries'] == 0

    retry.do_backoff()
    assert retry.should_run() is False
    assert retry.backoff['retries'] == 1
    scheduled_1 = retry.backoff['scheduled']
    retry.do_backoff()
    scheduled_2 = retry.backoff['scheduled']
    retry.do_backoff()
    scheduled_3 = retry.backoff['scheduled']
    retry.do_backoff()
    scheduled_4 = retry.backoff['scheduled']
    assert retry.backoff['retries'] == 4
    assert time.time() < scheduled_1 < scheduled_2 < scheduled_3 < scheduled_4
