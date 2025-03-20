# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import POSSIBLE_CONSUMER_GROUP_STATES

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_client_returns_expected_consumer_group_state(aggregator, check, kafka_instance, dd_run_check):
    check = check(kafka_instance)
    state = check.client.describe_consumer_group('my_consumer')
    assert state in POSSIBLE_CONSUMER_GROUP_STATES
