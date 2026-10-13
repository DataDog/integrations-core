# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors import COLLECT_FUNCTIONS, CollectContext, FirewallState
from datadog_checks.pan_firewall.collectors.licenses import LICENSE_INFO_CMD, collect_licenses, parse_licenses
from datadog_checks.pan_firewall.xml_utils import parse_response

from ..common import FW_A_TAGS
from ..fixture_map import op_fixture
from ..helpers import new_check

TODAY = datetime.date(2026, 10, 9)
FEATURES = {
    'adv_threat_prevention',
    'advanced_dns_security',
    'advanced_url_filtering',
    'advanced_wildfire_license',
    'dlp',
    'dns_security',
    'globalprotect_gateway',
    'pan_db_url_filtering',
    'pa_vm',
    'premium',
    'sd_wan',
    'threat_prevention',
    'virtual_systems',
    'wildfire_license',
}


def load(firewall):
    return parse_response(op_fixture(LICENSE_INFO_CMD, firewall).read_bytes())


def series(samples):
    result = {(s.name, s.tags): (s.value, s.kind) for s in samples}
    assert len(result) == len(samples)
    return result


def entry(root, feature):
    return next(e for e in root.iterfind('result/licenses/entry') if e.findtext('feature') == feature)


@pytest.mark.parametrize('firewall', ['fw-a', 'fw-b'])
def test_licenses_of_the_captures(firewall):
    samples = parse_licenses(load(firewall), mock.Mock(), TODAY)

    expected = {}
    for feature in FEATURES:
        expected['license.days_left', (f'feature:{feature}',)] = (13, 'gauge')
        expected['license.expired', (f'feature:{feature}',)] = (0, 'gauge')
    assert series(samples) == expected


def test_days_left_follows_the_date_it_is_given():
    samples = parse_licenses(load('fw-a'), mock.Mock(), datetime.date(2026, 10, 22))

    assert series(samples)['license.days_left', ('feature:pa_vm',)] == (0, 'gauge')


def test_expired_license_reports_one_and_negative_days():
    root = load('fw-a')
    entry(root, 'PA-VM').find('expired').text = 'yes'
    entry(root, 'PA-VM').find('expires').text = 'October 01, 2026'

    result = series(parse_licenses(root, mock.Mock(), TODAY))

    assert result['license.expired', ('feature:pa_vm',)] == (1, 'gauge')
    assert result['license.days_left', ('feature:pa_vm',)] == (-8, 'gauge')


def test_perpetual_license_has_no_days_left():
    root = load('fw-a')
    entry(root, 'PA-VM').find('expires').text = 'Never'

    result = series(parse_licenses(root, mock.Mock(), TODAY))

    assert result['license.expired', ('feature:pa_vm',)] == (0, 'gauge')
    assert ('license.days_left', ('feature:pa_vm',)) not in result
    assert len(result) == 27


def test_unparseable_date_reports_only_expired():
    root = load('fw-a')
    entry(root, 'PA-VM').find('expires').text = '22/10/2026'

    result = series(parse_licenses(root, mock.Mock(), TODAY))

    assert result['license.expired', ('feature:pa_vm',)] == (0, 'gauge')
    assert ('license.days_left', ('feature:pa_vm',)) not in result
    assert len(result) == 27


def test_unknown_shape_warns_and_sends_nothing():
    log = mock.Mock()

    samples = parse_licenses(parse_response(b'<response status="success"/>'), log, TODAY)

    assert samples == []
    log.warning.assert_called_once()


def test_collector_asks_for_the_license_info():
    ctx = CollectContext(
        client=mock.Mock(), identity=mock.Mock(), state=FirewallState(), config=mock.Mock(), log=mock.Mock()
    )
    ctx.client.op.return_value = load('fw-a')

    samples = collect_licenses(ctx)

    ctx.client.op.assert_called_once_with(LICENSE_INFO_CMD)
    assert len(samples) == 28


def test_licenses_are_registered_and_submit_through_the_check(real_collectors, dd_run_check, aggregator):
    assert 'licenses' in COLLECT_FUNCTIONS

    dd_run_check(new_check())

    tags = sorted([*FW_A_TAGS, 'feature:pan_db_url_filtering'])
    aggregator.assert_metric('pan_firewall.license.expired', 0, tags=tags, metric_type=aggregator.GAUGE)
    (days_left,) = [m for m in aggregator.metrics('pan_firewall.license.days_left') if sorted(m.tags) == tags]
    assert days_left.type == aggregator.GAUGE
    assert len(aggregator.metrics('pan_firewall.license.expired')) == 14
