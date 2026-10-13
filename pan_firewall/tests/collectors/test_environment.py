# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.system import ENVIRONMENTALS_CMD, collect_environment, parse_environmentals
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FIXTURES
from ..fixture_map import op_fixture
from ..test_check import FW_A_IP, FW_A_TAGS, new_check

HARDWARE = FIXTURES / 'synthetic' / 'environmentals_hw.xml'


def hardware():
    return parse_response(HARDWARE.read_bytes())


def series(samples):
    result = {(s.name, s.tags): (s.value, s.kind) for s in samples}
    assert len(result) == len(samples)
    return result


def sensor(description, slot):
    return f'sensor:{description}', f'slot:{slot}'


@pytest.mark.parametrize('firewall', ['fw-a', 'fw-b'])
def test_vm_series_has_no_sensors(firewall):
    log = mock.Mock()
    root = parse_response(op_fixture(ENVIRONMENTALS_CMD, firewall).read_bytes())

    assert parse_environmentals(root, log, set()) == []
    log.warning.assert_not_called()


def test_hardware_power_thresholds_and_alarms():
    result = series(parse_environmentals(hardware(), mock.Mock(), set()))

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


def test_alarm_without_a_direction_warns_once_per_sensor_and_firewall():
    log = mock.Mock()
    warned = set()

    parse_environmentals(hardware(), log, warned)
    parse_environmentals(hardware(), log, warned)

    log.warning.assert_called_once()
    assert 'Power Supply 5' in str(log.warning.call_args)
    # Another firewall has its own state, so it warns again.
    parse_environmentals(hardware(), log, set())
    assert log.warning.call_count == 2


def test_collector_asks_for_the_environmentals_and_keeps_the_warned_sensors():
    ctx = CollectContext(
        client=mock.Mock(), identity=mock.Mock(), state=FirewallState(), config=mock.Mock(), log=mock.Mock()
    )
    ctx.client.op.return_value = hardware()

    collect_environment(ctx)
    collect_environment(ctx)

    ctx.client.op.assert_called_with(ENVIRONMENTALS_CMD)
    ctx.log.warning.assert_called_once()


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


# Gated on the PA-3420 hardware capture (L8). Expected layout:
#   tests/fixtures/pa-3420/environmentals.xml   (`show system environmentals`)
#   tests/fixtures/pa-3420/interface_all.xml    (`show interface all`; see test_interfaces.py for the speeds)
#   tests/fixtures/pa-3420/system_info.xml      (`show system info`)
# When it lands, fix the field names in `parse_environmentals` if they differ, and delete the synthetic
# `environmentals_hw.xml` fixture together with the tests that use it once these pass.
PA_3420 = FIXTURES / 'pa-3420'
needs_pa_3420 = pytest.mark.skipif(
    not PA_3420.is_dir(), reason='Needs lab capture L8 (PA-3420 hardware): tests/fixtures/pa-3420/ missing'
)


@needs_pa_3420
def test_pa_3420_environmentals_parse_into_power_and_temperature_samples():
    log = mock.Mock()

    samples = parse_environmentals(parse_response((PA_3420 / 'environmentals.xml').read_bytes()), log, set())

    assert samples
    assert all(s.kind == 'gauge' for s in samples)
    assert {s.name.split('.')[0] for s in samples} <= {'power', 'temperature'}
    assert {'power.voltage', 'temperature.current'} <= {s.name for s in samples}
    assert all(any(tag.startswith('sensor:') for tag in s.tags) for s in samples)
    assert all(s.value >= 0 for s in samples if s.name.endswith(('.alarm', '.alarm.high', '.alarm.low')))
    series(samples)
    log.warning.assert_not_called()
