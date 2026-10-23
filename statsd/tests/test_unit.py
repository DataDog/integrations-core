# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.statsd.statsd import SERVICE_CHECK_NAME, SERVICE_CHECK_NAME_HEALTH, StatsCheck

pytestmark = pytest.mark.unit

CHECK_NAME = "statsd"

# Every _send_command call gets its own FakeSocket, keyed off of the command it sends
# ("health", "stats", "counters", "gauges", "timers"). Values are either a single bytes
# chunk or a list of chunks to be returned by successive recv() calls.
BASE_RESPONSES = {
    "health": b"health: up\n",
    "stats": b"END\n",
    "counters": b"c1\nc2\nc3\nEND\n",
    "gauges": b"g1\ng2\ng3\nEND\n",
    "timers": b"t1\nt2\nt3\nEND\n",
}


class FakeSocket:
    def __init__(self, responses):
        self.responses = responses
        self.chunks = []
        self.timeout = None

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, address):
        pass

    def sendall(self, data):
        command = data.decode().strip()
        chunks = self.responses[command]
        self.chunks = list(chunks) if isinstance(chunks, list) else [chunks]

    def recv(self, bufsize):
        assert bufsize == 1024
        if self.chunks:
            return self.chunks.pop(0)
        return b""

    def close(self):
        pass


def fake_socket_factory(responses, created=None):
    def factory(*args, **kwargs):
        sock = FakeSocket(responses)
        if created is not None:
            created.append(sock)
        return sock

    return factory


def test_check_uses_default_host_port_and_timeout_when_omitted(aggregator):
    created = []
    with mock.patch(
        "datadog_checks.statsd.statsd.socket.socket", side_effect=fake_socket_factory(BASE_RESPONSES, created)
    ):
        check = StatsCheck(CHECK_NAME, {}, {})
        check.check({})

    expected_tags = ["host:localhost", "port:8126"]
    aggregator.assert_service_check(SERVICE_CHECK_NAME_HEALTH, tags=expected_tags, count=1)
    assert created
    assert all(sock.timeout == 10.0 for sock in created)


@pytest.mark.parametrize(
    "health_response, expected_status",
    [
        (b"health: up\n", AgentCheck.OK),
        (b"health: aaa\n", AgentCheck.CRITICAL),
        (b"health: zzz\n", AgentCheck.CRITICAL),
    ],
)
def test_health_service_check_requires_exact_match_with_health_up(aggregator, health_response, expected_status):
    responses = dict(BASE_RESPONSES, health=health_response)
    with mock.patch("datadog_checks.statsd.statsd.socket.socket", side_effect=fake_socket_factory(responses)):
        check = StatsCheck(CHECK_NAME, {}, {})
        check.check({"host": "h", "port": 1})

    aggregator.assert_service_check(SERVICE_CHECK_NAME_HEALTH, status=expected_status, count=1)


STATS_RESPONSE = b"average:1\nbad_lines_seen:5\nuptime:100\nmalformed:not_a_number:extra\nEND\n"


def test_stats_line_parsing_routes_bad_lines_seen_to_monotonic_count(aggregator):
    responses = dict(BASE_RESPONSES, stats=STATS_RESPONSE)
    with mock.patch("datadog_checks.statsd.statsd.socket.socket", side_effect=fake_socket_factory(responses)):
        check = StatsCheck(CHECK_NAME, {}, {})
        check.check({"host": "h", "port": 1})

    aggregator.assert_metric("statsd.bad_lines_seen", value=5.0, count=1, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric("statsd.average", value=1.0, count=1, metric_type=aggregator.GAUGE)
    aggregator.assert_metric("statsd.uptime", value=100.0, count=1, metric_type=aggregator.GAUGE)
    aggregator.assert_metric("statsd.malformed", count=0)
    aggregator.assert_metric("statsd.not_a_number", count=0)


def test_counters_gauges_timers_counts_exclude_the_trailing_end_line(aggregator):
    responses = dict(BASE_RESPONSES, counters=[b"c1\nc2\n", b"c3\nEND\n"])
    with mock.patch("datadog_checks.statsd.statsd.socket.socket", side_effect=fake_socket_factory(responses)):
        check = StatsCheck(CHECK_NAME, {}, {})
        check.check({"host": "h", "port": 1})

    aggregator.assert_metric("statsd.counters.count", value=3, count=1)
    aggregator.assert_metric("statsd.gauges.count", value=3, count=1)
    aggregator.assert_metric("statsd.timers.count", value=3, count=1)


class RaisingSocket:
    def settimeout(self, timeout):
        pass

    def connect(self, address):
        raise RuntimeError("boom")

    def close(self):
        pass


def test_send_command_wraps_socket_errors_as_failed_connection(aggregator):
    with mock.patch("datadog_checks.statsd.statsd.socket.socket", return_value=RaisingSocket()):
        check = StatsCheck(CHECK_NAME, {}, {})
        with pytest.raises(Exception, match="Failed connection"):
            check.check({"host": "h", "port": 1})

    aggregator.assert_service_check(SERVICE_CHECK_NAME, status=AgentCheck.CRITICAL, count=1)
