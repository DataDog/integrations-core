# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from xml.etree import ElementTree as ET

import pytest

from datadog_checks.pan_firewall import PanFirewallCheck
from datadog_checks.pan_firewall.errors import PanosApiError
from datadog_checks.pan_firewall.xml_utils import num, parse_response, text

from .common import FIXTURES
from .fixture_map import OP_FIXTURES, op_fixture

SYSTEM_INFO_CMD = '<show><system><info/></system></show>'

# Patterns that mean a credential value was captured. The bare word "password" is not one of them: real fixtures
# legitimately contain `<password-set>no</password-set>` and threat names such as "/etc/passwd Access Attempt".
SECRET_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (r'<key>', r'LUFRPT', r'<password>', r'password=', r'key=', r'X-PAN-KEY', r'Cookie:')
]


def test_check_runs(dd_run_check, instance):
    dd_run_check(PanFirewallCheck('pan_firewall', {}, [instance]))


def test_parse_response_system_info():
    root = parse_response(op_fixture(SYSTEM_INFO_CMD).read_bytes())

    assert root.get('status') == 'success'
    assert text(root, './result/system/hostname') == 'fw-a'
    assert text(root, './result/system/sw-version') == '11.1.13-h12'
    assert num(root, './result/system/vm-cores') == 4


def test_parse_response_error_code():
    body = (FIXTURES / 'fw-a-probe' / 'report_top-rules.xml').read_bytes()

    with pytest.raises(PanosApiError) as exc_info:
        parse_response(body)

    assert exc_info.value.code == '400'
    assert 'Illegal value for parameter "reportname"' in exc_info.value.msg


def test_parse_response_error_without_code():
    with pytest.raises(PanosApiError) as exc_info:
        parse_response(b'<response status="error"><msg><line>Invalid credentials.</line></msg></response>')

    assert exc_info.value.code == ''
    assert exc_info.value.msg == 'Invalid credentials.'


@pytest.mark.parametrize(
    'body',
    [
        b'<html><body>Bad Gateway',
        b'',
        b'not xml at all',
        # A proxy error page that happens to be well-formed XML must not pass as a PAN-OS success.
        b'<html><body>502 Bad Gateway</body></html>',
    ],
)
def test_parse_response_non_xml(body):
    with pytest.raises(PanosApiError) as exc_info:
        parse_response(body)

    assert exc_info.value.code == 'parse'


@pytest.mark.parametrize(
    'xml, path, expected',
    [
        ('<r><v>3.5</v></r>', 'v', 3.5),
        ('<r><v> 7 </v></r>', 'v', 7.0),
        ('<r><v>unknown</v></r>', 'v', None),
        ('<r><v></v></r>', 'v', None),
        ('<r></r>', 'v', None),
        ('<r><v>nan</v></r>', 'v', None),
        ('<r><v>-inf</v></r>', 'v', None),
    ],
)
def test_num_never_raises(xml, path, expected):
    assert num(ET.fromstring(xml), path) == expected


def test_num_and_text_on_missing_element():
    assert num(None, 'v') is None
    assert text(None, 'v', 'fallback') == 'fallback'


def test_fixture_map_points_at_existing_files():
    for firewall in ('fw-a', 'fw-b'):
        for cmd in OP_FIXTURES:
            assert op_fixture(cmd, firewall).is_file()


def test_fixtures_hold_no_secrets():
    files = [p for p in FIXTURES.rglob('*') if p.is_file()]
    assert files
    leaks = [
        (p.relative_to(FIXTURES).as_posix(), pattern.pattern)
        for p in files
        for pattern in SECRET_PATTERNS
        if pattern.search(p.read_text(encoding='utf-8', errors='replace'))
    ]
    assert leaks == []
