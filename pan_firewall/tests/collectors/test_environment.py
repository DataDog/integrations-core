# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS
from datadog_checks.pan_firewall.collectors.system import ENVIRONMENTALS_CMD, parse_environmentals

from ..common import FIXTURES, FW_A_IP, FW_A_TAGS
from ..helpers import load_op, load_xml, new_check, series

HARDWARE = FIXTURES / 'synthetic' / 'environmentals_hw.xml'


def hardware():
    return load_xml(HARDWARE)


def sensor(description, slot):
    return f'sensor:{description}', f'slot:{slot}'


def test_vm_series_has_no_sensors():
    log = mock.Mock()

    assert parse_environmentals(load_op(ENVIRONMENTALS_CMD), log, set()) == []
    log.warning.assert_not_called()


def test_hardware_power_thresholds_and_alarms():
    log = mock.Mock()
    result = series(parse_environmentals(hardware(), log, set()))

    def power(description, slot, **values):
        return {(f'power.{name}', sensor(description, slot)): (value, 'gauge') for name, value in values.items()}

    expected = {}
    # `min`/`max` and the `min-volt`/`max-volt` fallback both send the thresholds.
    expected |= power('Power Supply 1', 1, voltage=12.1, **{'voltage.min': 10.8, 'voltage.max': 13.2}) | power(
        'Power Supply 1', 1, **{'alarm.high': 0, 'alarm.low': 0}
    )
    expected |= power('Power Supply 2', 1, voltage=11.9, **{'voltage.min': 10.6, 'voltage.max': 13.4}) | power(
        'Power Supply 2', 1, **{'alarm.high': 0, 'alarm.low': 0}
    )
    expected |= power('Power Supply 3', 1, voltage=13.9, **{'voltage.min': 10.8, 'voltage.max': 13.2}) | power(
        'Power Supply 3', 1, **{'alarm.high': 1, 'alarm.low': 0}
    )
    # PAN's `alarm` field wins over the voltage being above the maximum.
    expected |= power('Power Supply 4', 1, voltage=13.9, **{'voltage.min': 10.8, 'voltage.max': 13.2}) | power(
        'Power Supply 4', 1, **{'alarm.high': 0, 'alarm.low': 0}
    )
    # Alarm without thresholds: the direction is unknown, so no alarm metric.
    expected |= power('Power Supply 5', 1, voltage=12.0)
    expected |= power('Power Supply 6', 2, voltage=10.2, **{'voltage.min': 10.8, 'voltage.max': 13.2}) | power(
        'Power Supply 6', 2, **{'alarm.high': 0, 'alarm.low': 1}
    )
    power_series = {k: v for k, v in result.items() if k[0].startswith('power.')}
    assert power_series == expected
    log.warning.assert_called_once()
    assert 'Power Supply 5' in str(log.warning.call_args)


def test_hardware_thermal_values_and_alarm():
    result = series(parse_environmentals(hardware(), mock.Mock(), set()))

    expected = {}
    for description, degrees, alarm in (
        ('Temperature at Inlet', 31.0, 0),
        ('Temperature at CPU', 85.5, 1),
        ('Temperature at Exhaust', 82.0, 1),
    ):
        tags = sensor(description, 1)
        expected['temperature.current', tags] = (degrees, 'gauge')
        expected['temperature.min', tags] = (0.0, 'gauge')
        expected['temperature.max', tags] = (80.0, 'gauge')
        expected['temperature.alarm', tags] = (alarm, 'gauge')
    assert {k: v for k, v in result.items() if k[0].startswith('temperature.')} == expected


def test_environment_is_registered_and_submits_through_the_check(real_collectors, fake_panos, dd_run_check, aggregator):
    assert 'environment' in COLLECT_FUNCTIONS
    fake_panos.answer_op(FW_A_IP, ENVIRONMENTALS_CMD, (200, HARDWARE.read_bytes()))

    dd_run_check(new_check())

    tags = sorted([*FW_A_TAGS, 'sensor:Power Supply 3', 'slot:1'])
    aggregator.assert_metric('pan_firewall.power.voltage', 13.9, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('pan_firewall.power.alarm.high', 1, tags=tags, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('pan_firewall.power.alarm.low', 0, tags=tags, metric_type=aggregator.GAUGE)
    cpu = sorted([*FW_A_TAGS, 'sensor:Temperature at CPU', 'slot:1'])
    aggregator.assert_metric('pan_firewall.temperature.current', 85.5, tags=cpu, metric_type=aggregator.GAUGE)
    aggregator.assert_metric('pan_firewall.temperature.alarm', 1, tags=cpu, metric_type=aggregator.GAUGE)
    assert len(aggregator.metrics('pan_firewall.temperature.current')) == 3
