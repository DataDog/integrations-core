import json

from datadog_checks.base.checks.base import AgentCheck
from datadog_checks.base.utils.db.telemetry import Telemetry


class MockCheck(AgentCheck):
    resolved_hostname = ''

    def __init__(self):
        self.events = []

    def database_monitoring_query_metrics(self, event):
        self.events.append(json.loads(event))

    def _get_debug_tags(self):
        return []

    def count(self, _k, _c, **kwargs):
        return None


def test_telemetry():
    mock = MockCheck()
    telemetry = Telemetry(mock)
    telemetry._last_flush = 0
    telemetry.add("test", 1, None)
    assert len(mock.events) == 1
    assert mock.events[0]["integration"] == "mockcheck"
    assert mock.events[0]["operation"] == "test"
    assert mock.events[0]["elapsed"] == 1
    assert mock.events[0]["count"] is None
