# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.licenses import LICENSE_INFO_CMD, parse_licenses

from ..helpers import load_op, series

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


def entry(root, feature):
    return next(e for e in root.iterfind('result/licenses/entry') if e.findtext('feature') == feature)


def test_licenses_of_the_capture():
    samples = parse_licenses(load_op(LICENSE_INFO_CMD), mock.Mock(), mock.Mock(), TODAY)

    expected = {}
    for feature in FEATURES:
        expected['license.days_left', (f'feature:{feature}',)] = (13, 'gauge')
        expected['license.expired', (f'feature:{feature}',)] = (0, 'gauge')
    assert series(samples) == expected


def test_expired_license_reports_one_and_negative_days():
    root = load_op(LICENSE_INFO_CMD)
    entry(root, 'PA-VM').find('expired').text = 'yes'
    entry(root, 'PA-VM').find('expires').text = 'October 01, 2026'

    result = series(parse_licenses(root, mock.Mock(), mock.Mock(), TODAY))

    assert result['license.expired', ('feature:pa_vm',)] == (1, 'gauge')
    assert result['license.days_left', ('feature:pa_vm',)] == (-8, 'gauge')


@pytest.mark.parametrize('expires', ['Never', '22/10/2026'], ids=['perpetual', 'unparseable-date'])
def test_license_without_a_usable_expiry_reports_only_expired(expires):
    root = load_op(LICENSE_INFO_CMD)
    entry(root, 'PA-VM').find('expires').text = expires

    result = series(parse_licenses(root, mock.Mock(), mock.Mock(), TODAY))

    assert result['license.expired', ('feature:pa_vm',)] == (0, 'gauge')
    assert ('license.days_left', ('feature:pa_vm',)) not in result
    assert len(result) == 27
