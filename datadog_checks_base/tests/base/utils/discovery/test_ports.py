# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.discovery.ports import candidate_ports
from datadog_checks.base.utils.discovery.service import Port, Service


def _svc(*ports):
    return Service(id="x", host="h", ports=tuple(ports))


def test_hint_first_then_rest():
    svc = _svc(Port(8080), Port(9090), Port(80))
    assert list(candidate_ports(svc, [9090])) == [Port(9090), Port(8080), Port(80)]


def test_multiple_hints_in_order():
    svc = _svc(Port(80), Port(8080), Port(9090))
    assert list(candidate_ports(svc, [9090, 8080])) == [Port(9090), Port(8080), Port(80)]


def test_hint_not_exposed_skipped():
    svc = _svc(Port(80))
    assert list(candidate_ports(svc, [9090])) == [Port(80)]


def test_no_hints_returns_service_order():
    svc = _svc(Port(80), Port(9090))
    assert list(candidate_ports(svc, [])) == [Port(80), Port(9090)]


def test_no_ports_returns_empty():
    svc = _svc()
    assert list(candidate_ports(svc, [9090])) == []


def test_no_duplicates_when_hint_repeats():
    svc = _svc(Port(9090))
    assert list(candidate_ports(svc, [9090, 9090])) == [Port(9090)]
