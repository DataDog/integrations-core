# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock
import pytest

from datadog_checks.base import AgentCheck
from datadog_checks.statsd.statsd import SERVICE_CHECK_NAME, SERVICE_CHECK_NAME_HEALTH, StatsCheck

pytestmark = pytest.mark.unit

CHECK_NAME = 'statsd'

# Every _send_command call gets its own FakeSocket, keyed off of the command it sends
# ("health", "stats", "counters", "gauges", "timers"). Values are either a single bytes
# chunk or a list of chunks to be returned by successive recv() calls.
BASE_RESPONSES = {
    'health': b"health: up\n",
    'stats': b"END\n",
    'counters': b"c1\nc2\nc3\nEND\n",
    'gauges': b"g1\ng2\ng3\nEND\n",
    'timers': b"t1\nt2\nt3\nEND\n",
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
        # Kills the core/NumberReplacer mutants at statsd.py:68 and statsd.py:75 (recv(1024) -> 1023/1025).
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
    # Kills the core/NumberReplacer mutants at statsd.py:21 (port default 8126 -> 8127/8125) and
    # statsd.py:22 (timeout default 10 -> 11/9): with no host/port/timeout in the instance, the
    # emitted tags and every socket's timeout must reflect exactly the documented defaults.
    created = []
    with mock.patch(
        'datadog_checks.statsd.statsd.socket.socket', side_effect=fake_socket_factory(BASE_RESPONSES, created)
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
        (b"health: aaa\n", AgentCheck.CRITICAL),  # lexically < "health: up", kills Eq_LtE mutant
        (b"health: zzz\n", AgentCheck.CRITICAL),  # lexically > "health: up", kills Eq_GtE mutant
    ],
)
def test_health_service_check_requires_exact_match_with_health_up(aggregator, health_response, expected_status):
    # Kills the core/ReplaceComparisonOperator_Eq_LtE, Eq_GtE and Eq_IsNot mutants at statsd.py:28
    # (health == b"health: up" swapped for <=, >= or is not), any of which would flip the resulting
    # service check status for a value that is lexically ordered around, or merely non-identical to,
    # b"health: up".
    responses = dict(BASE_RESPONSES, health=health_response)
    with mock.patch('datadog_checks.statsd.statsd.socket.socket', side_effect=fake_socket_factory(responses)):
        check = StatsCheck(CHECK_NAME, {}, {})
        check.check({'host': 'h', 'port': 1})

    aggregator.assert_service_check(SERVICE_CHECK_NAME_HEALTH, status=expected_status, count=1)


STATS_RESPONSE = (
    b"average:1\n"  # lexically before "bad_lines_seen", kills Eq_LtE mutant at statsd.py:41
    b"bad_lines_seen:5\n"  # the exact monotonic_count key, kills most comparison mutants at statsd.py:41-42
    b"uptime:100\n"  # lexically after "bad_lines_seen", kills Eq_GtE/Eq_IsNot mutants at statsd.py:41
    b"malformed:not_a_number:extra\n"  # 3 parts, kills the len(parts) == 2 -> >= 2 mutant at statsd.py:38
    b"END\n"
)


def test_stats_line_parsing_routes_bad_lines_seen_to_monotonic_count(aggregator):
    # Kills the core/ReplaceComparisonOperator (NotEq/Lt/LtE/Gt/GtE/Is/IsNot), core/AddNot and
    # core/NumberReplacer(parts[1]/parts[-1]) mutants at statsd.py:41-42: only the exact
    # "bad_lines_seen" key must route to monotonic_count under its own name and value, every other
    # 2-part line must route to gauge, and a stray 3-part line must be skipped instead of crashing
    # on an unparsable float (which is what the len(parts) == 2 -> >= 2 mutant at statsd.py:38 would do).
    responses = dict(BASE_RESPONSES, stats=STATS_RESPONSE)
    with mock.patch('datadog_checks.statsd.statsd.socket.socket', side_effect=fake_socket_factory(responses)):
        check = StatsCheck(CHECK_NAME, {}, {})
        check.check({'host': 'h', 'port': 1})

    aggregator.assert_metric('statsd.bad_lines_seen', value=5.0, count=1, metric_type=aggregator.MONOTONIC_COUNT)
    aggregator.assert_metric('statsd.average', value=1.0, count=1, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('statsd.uptime', value=100.0, count=1, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('statsd.malformed', count=0)
    aggregator.assert_metric('statsd.not_a_number', count=0)


def test_counters_gauges_timers_counts_exclude_the_trailing_end_line(aggregator):
    # Kills the core/ReplaceBinaryOperator_Sub_* and core/NumberReplacer(-1 -> -2/-0) mutants at
    # statsd.py:46, :49 and :52: each response has 3 data lines plus a trailing "END" line, so the
    # correct count (splitlines() - 1) is 3, a value every other operator variant produces differently.
    # The multi-chunk "counters" response also forces a second recv() call, exercising statsd.py:75.
    responses = dict(BASE_RESPONSES, counters=[b"c1\nc2\n", b"c3\nEND\n"])
    with mock.patch('datadog_checks.statsd.statsd.socket.socket', side_effect=fake_socket_factory(responses)):
        check = StatsCheck(CHECK_NAME, {}, {})
        check.check({'host': 'h', 'port': 1})

    aggregator.assert_metric('statsd.counters.count', value=3, count=1)
    aggregator.assert_metric('statsd.gauges.count', value=3, count=1)
    aggregator.assert_metric('statsd.timers.count', value=3, count=1)


class RaisingSocket:
    def settimeout(self, timeout):
        pass

    def connect(self, address):
        raise RuntimeError("boom")

    def close(self):
        pass


def test_send_command_wraps_socket_errors_as_failed_connection(aggregator):
    # Kills the core/ExceptionReplacer mutant at statsd.py:78 (except Exception -> except
    # CosmicRayTestingException): with the mutant, the underlying socket error would escape
    # unwrapped instead of being caught, reported as a CRITICAL service check, and re-raised with
    # a "Failed connection" message.
    with mock.patch('datadog_checks.statsd.statsd.socket.socket', return_value=RaisingSocket()):
        check = StatsCheck(CHECK_NAME, {}, {})
        with pytest.raises(Exception, match="Failed connection"):
            check.check({'host': 'h', 'port': 1})

    aggregator.assert_service_check(SERVICE_CHECK_NAME, status=AgentCheck.CRITICAL, count=1)
