# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import pytest

from datadog_checks.base.utils.discovery.service import Port, Service


def test_port_defaults():
    p = Port(number=9090)
    assert p.number == 9090
    assert p.name == ""


def test_port_with_name():
    p = Port(number=9090, name="metrics")
    assert p.name == "metrics"


def test_port_is_hashable():
    {Port(9090), Port(9091, "metrics")}


def test_port_is_immutable():
    p = Port(9090)
    with pytest.raises(Exception):
        p.number = 9091  # type: ignore[misc]


def test_service_basic():
    svc = Service(id="docker://abc", host="10.0.0.1", ports=(Port(9090),))
    assert svc.id == "docker://abc"
    assert svc.host == "10.0.0.1"
    assert svc.ports == (Port(9090),)


def test_service_is_hashable():
    {Service(id="a", host="h", ports=(Port(1),))}


def test_service_ports_is_tuple_not_list():
    svc = Service(id="a", host="h", ports=(Port(1), Port(2)))
    assert isinstance(svc.ports, tuple)
