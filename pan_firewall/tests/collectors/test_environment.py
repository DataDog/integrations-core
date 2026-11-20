# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.system import ENVIRONMENTALS_CMD, parse_environmentals
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import SYNTHETIC
from ..helpers import load_op, load_xml, series

pytestmark = pytest.mark.unit

# The sensors of `synthetic/environmentals_hw.xml`, which explains each case; None is a series not sent.
# (sensor, slot, voltage, voltage.min, voltage.max, alarm, alarm.high, alarm.low)
POWER = [
    ('Power Supply 1', 1, 12.1, 10.8, 13.2, 0, 0, 0),
    ('Power Supply 2', 1, 11.9, 10.6, 13.4, 0, 0, 0),
    ('Power Supply 3', 1, 13.9, 10.8, 13.2, 1, 1, 0),
    ('Power Supply 4', 1, 13.9, 10.8, 13.2, 0, 0, 0),
    ('Power Supply 5', 1, 12.0, None, None, 1, None, None),
    ('Power Supply 6', 2, 10.2, 10.8, 13.2, 1, 0, 1),
]
# (sensor, current, alarm), all in slot 1 with min 0 and max 80.
THERMAL = [
    ('Temperature at Inlet', 31.0, 0),
    ('Temperature at CPU', 85.5, 1),
    ('Temperature at Exhaust', 82.0, 1),
]
# (sensor, speed, alarm), all in slot 1 with a minimum of 2000.
FANS = [
    ('Fan #1 RPM', 3600.0, 0),
    ('Fan #2 RPM', 0.0, 1),
]
# (sensor, alarm, inserted), all in slot 1.
POWER_SUPPLIES = [
    ('Power Supply #1 (left)', 0, 1),
    ('Power Supply #2 (right)', 1, 0),
]


def test_vm_series_has_no_sensors():
    assert parse_environmentals(load_op(ENVIRONMENTALS_CMD), mock.Mock()) == []


def test_hardware_sensors():
    expected = {}
    for sensor, slot, *values in POWER:
        names = ('voltage', 'voltage.min', 'voltage.max', 'alarm', 'alarm.high', 'alarm.low')
        for name, value in zip(names, values):
            if value is not None:
                expected[f'power.{name}', (f'sensor:{sensor}', f'slot:{slot}')] = (value, 'gauge')
    for sensor, current, alarm in THERMAL:
        for name, value in (('current', current), ('min', 0.0), ('max', 80.0), ('alarm', alarm)):
            expected[f'temperature.{name}', (f'sensor:{sensor}', 'slot:1')] = (value, 'gauge')
    for sensor, speed, alarm in FANS:
        for name, value in (('speed', speed), ('speed.min', 2000.0), ('alarm', alarm)):
            expected[f'fan.{name}', (f'sensor:{sensor}', 'slot:1')] = (value, 'gauge')
    for sensor, alarm, inserted in POWER_SUPPLIES:
        for name, value in (('alarm', alarm), ('inserted', inserted)):
            expected[f'power_supply.{name}', (f'sensor:{sensor}', 'slot:1')] = (value, 'gauge')

    assert series(parse_environmentals(load_xml(SYNTHETIC / 'environmentals_hw.xml'), mock.Mock())) == expected


def test_fans_section_named_fans():
    """The PA-5410 names the fan section `fans` instead of `fan`."""
    root = parse_response(
        b'<response status="success"><result><fans><Slot1><entry><slot>1</slot>'
        b'<description>Inlet fan of Fan unit #1</description><alarm>False</alarm><RPMs>2436</RPMs><min>2000</min>'
        b'</entry></Slot1></fans></result></response>'
    )
    tags = ('sensor:Inlet fan of Fan unit #1', 'slot:1')

    assert series(parse_environmentals(root, mock.Mock())) == {
        ('fan.speed', tags): (2436.0, 'gauge'),
        ('fan.speed.min', tags): (2000.0, 'gauge'),
        ('fan.alarm', tags): (0, 'gauge'),
    }
