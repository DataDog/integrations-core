# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from .common import assert_check_kafka

pytestmark = [pytest.mark.e2e]


@pytest.fixture(autouse=True)
def _time_get_highwater_offsets(monkeypatch, request):
    import time

    from datadog_checks.kafka_consumer.kafka_consumer import KafkaCheck

    original = KafkaCheck.get_highwater_offsets

    def wrapped(self, *args, **kwargs):
        start = time.perf_counter()
        try:
            return original(self, *args, **kwargs)
        finally:
            duration = time.perf_counter() - start
            print(f"[perf] {request.node.nodeid} get_highwater_offsets: {duration:.3f}s")

    monkeypatch.setattr(KafkaCheck, 'get_highwater_offsets', wrapped)
    yield


def test_e2e(dd_agent_check, kafka_instance):
    aggregator = dd_agent_check(kafka_instance)
    assert_check_kafka(aggregator, kafka_instance['consumer_groups'])
