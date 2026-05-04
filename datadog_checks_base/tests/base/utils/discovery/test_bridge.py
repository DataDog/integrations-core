# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

from datadog_checks.base.utils.discovery._bridge import _run_discover
from datadog_checks.base.utils.discovery.service import Service


class _Found:
    @classmethod
    def discover(cls, service: Service):
        return [{"openmetrics_endpoint": f"http://{service.host}:{service.ports[0].number}/metrics"}]


class _NotFound:
    @classmethod
    def discover(cls, service: Service):
        return None


class _EmptyList:
    @classmethod
    def discover(cls, service: Service):
        return []


class _Raises:
    @classmethod
    def discover(cls, service: Service):
        raise RuntimeError("boom")


SVC_JSON = json.dumps(
    {
        "id": "docker://abc",
        "host": "10.0.0.1",
        "ports": [{"number": 9090, "name": "metrics"}],
    }
)


def test_bridge_returns_json_list_on_match():
    out = _run_discover(_Found, SVC_JSON)
    parsed = json.loads(out)
    assert parsed == [{"openmetrics_endpoint": "http://10.0.0.1:9090/metrics"}]


def test_bridge_returns_null_on_no_match():
    assert _run_discover(_NotFound, SVC_JSON) == "null"


def test_bridge_returns_empty_list_on_explicit_empty():
    assert _run_discover(_EmptyList, SVC_JSON) == "[]"


def test_bridge_returns_null_on_exception():
    assert _run_discover(_Raises, SVC_JSON) == "null"


def test_bridge_constructs_service_correctly():
    captured = {}

    class C:
        @classmethod
        def discover(cls, service: Service):
            captured["id"] = service.id
            captured["host"] = service.host
            captured["ports"] = [(p.number, p.name) for p in service.ports]
            return None

    _run_discover(C, SVC_JSON)
    assert captured == {
        "id": "docker://abc",
        "host": "10.0.0.1",
        "ports": [(9090, "metrics")],
    }


def test_bridge_handles_missing_discover_method():
    class NoDiscover:
        pass

    assert _run_discover(NoDiscover, SVC_JSON) == "null"
