# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
from unittest import mock

import pytest

from datadog_checks.pan_firewall.collectors.licenses import LICENSE_INFO_CMD, parse_licenses

from ..helpers import load_op, series

pytestmark = pytest.mark.unit

TODAY = datetime.date(2026, 10, 9)
# Every license of the capture expires on October 22, 2026.
FEATURES = (
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
)


def test_licenses_of_the_capture():
    samples = parse_licenses(load_op(LICENSE_INFO_CMD), mock.Mock(), mock.Mock(), TODAY)

    assert series(samples) == {
        (name, (f'feature:{feature}',)): (value, 'gauge')
        for feature in FEATURES
        for name, value in (('license.days_left', 13), ('license.expired', 0))
    }


@pytest.mark.parametrize(
    'expired, expires, expected',
    [
        pytest.param('yes', 'October 01, 2026', {'license.expired': 1, 'license.days_left': -8}, id='expired'),
        pytest.param('no', 'Never', {'license.expired': 0}, id='perpetual'),
        pytest.param('no', '22/10/2026', {'license.expired': 0}, id='unparseable-date'),
    ],
)
def test_license_expiry(expired, expires, expected):
    root = load_op(LICENSE_INFO_CMD)
    entry = root.find("result/licenses/entry[feature='PA-VM']")
    entry.find('expired').text = expired
    entry.find('expires').text = expires

    samples = parse_licenses(root, mock.Mock(), mock.Mock(), TODAY)

    assert {s.name: s.value for s in samples if s.tags == ('feature:pa_vm',)} == expected
