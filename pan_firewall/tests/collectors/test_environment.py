# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.system import ENVIRONMENTALS_CMD, parse_environmentals

from ..common import SYNTHETIC
from ..helpers import load_op, load_xml, series

pytestmark = pytest.mark.unit

# The sensors of `synthetic/environmentals_hw.xml`, which explains each case; None is a series not sent.
# (sensor, slot, voltage, voltage.min, voltage.max, alarm.high, alarm.low)
POWER = [
    ('Power Supply 1', 1, 12.1, 10.8, 13.2, 0, 0),
    ('Power Supply 2', 1, 11.9, 10.6, 13.4, 0, 0),
    ('Power Supply 3', 1, 13.9, 10.8, 13.2, 1, 0),
    ('Power Supply 4', 1, 13.9, 10.8, 13.2, 0, 0),
    ('Power Supply 5', 1, 12.0, None, None, None, None),
    ('Power Supply 6', 2, 10.2, 10.8, 13.2, 0, 1),
]
# (sensor, current, alarm), all in slot 1 with min 0 and max 80.
THERMAL = [
    ('Temperature at Inlet', 31.0, 0),
    ('Temperature at CPU', 85.5, 1),
    ('Temperature at Exhaust', 82.0, 1),
]


def test_vm_series_has_no_sensors():
    assert parse_environmentals(load_op(ENVIRONMENTALS_CMD), mock.Mock()) == []


def test_hardware_sensors():
    expected = {}
    for sensor, slot, *values in POWER:
        names = ('voltage', 'voltage.min', 'voltage.max', 'alarm.high', 'alarm.low')
        for name, value in zip(names, values):
            if value is not None:
                expected[f'power.{name}', (f'sensor:{sensor}', f'slot:{slot}')] = (value, 'gauge')
    for sensor, current, alarm in THERMAL:
        for name, value in (('current', current), ('min', 0.0), ('max', 80.0), ('alarm', alarm)):
            expected[f'temperature.{name}', (f'sensor:{sensor}', 'slot:1')] = (value, 'gauge')

    assert series(parse_environmentals(load_xml(SYNTHETIC / 'environmentals_hw.xml'), mock.Mock())) == expected
