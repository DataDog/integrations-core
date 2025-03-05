# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

pytestmark = [pytest.mark.integration, pytest.mark.usefixtures('dd_environment')]


def test_client_returns_expected_consumer_group_state(aggregator, check, kafka_instance, dd_run_check):
    check = check(kafka_instance)
    assert check.client.describe_consumer_groups('my_consumer') == ('my_consumer', 'STABLE')
