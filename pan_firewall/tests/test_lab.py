# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from .common import build_lab_instance, e2e_addresses
from .test_check import new_check

PASSWORD = 'lab-password-must-not-leak'
PANORAMA_PASSWORD = 'panorama-password-must-not-leak'
STATIC_ENV = {
    'PANOS_LAB_MODE': 'static',
    'PANOS_LAB_HOSTS': '192.0.2.10',
    'PANOS_LAB_USERNAME': 'lab-user',
    'PANOS_PASSWORD': PASSWORD,
}
PANORAMA_ENV = {
    'PANOS_LAB_MODE': 'panorama',
    'PANOS_LAB_PANORAMA_HOST': 'panorama.example.com',
    'PANOS_LAB_PANORAMA_USERNAME': 'panorama-user',
    'PANOS_LAB_PANORAMA_PASSWORD': PANORAMA_PASSWORD,
    'PANOS_LAB_USERNAME': 'lab-user',
    'PANOS_PASSWORD': PASSWORD,
    'PANOS_LAB_FIREWALL_OVERRIDES': '007955000930601=192.0.2.10,007955000930602=192.0.2.11',
}


def test_lab_password_never_leaks(caplog, aggregator):
    # An explicit mapping, never the real environment: a lab variable exported in the developer's shell must not
    # change which mode (or whose password) this test builds.
    instance = build_lab_instance(STATIC_ENV)
    assert instance['firewall_credentials'][0]['password'] == PASSWORD

    check = new_check(instance)
    with caplog.at_level(logging.DEBUG):
        check.run()

    # Not `repr(check.config)`: generated pydantic models keep secrets as plain `str`, so it shows the password.
    # That is true of every integration, and the check never logs or prints its config.
    exposed = {'log': caplog.text, 'check': repr(check), 'check str': str(check)}
    assert [name for name, text in exposed.items() if PASSWORD in text] == []


def test_lab_panorama_passwords_never_leak(caplog, aggregator):
    instance = build_lab_instance(PANORAMA_ENV)
    assert instance['panorama_password'] == PANORAMA_PASSWORD

    check = new_check(instance)
    with caplog.at_level(logging.DEBUG):
        check.run()

    exposed = {'log': caplog.text, 'check': repr(check), 'check str': str(check)}
    leaks = [
        (name, secret) for name, text in exposed.items() for secret in (PASSWORD, PANORAMA_PASSWORD) if secret in text
    ]
    assert leaks == []


@pytest.mark.parametrize('missing', ['PANOS_LAB_HOSTS', 'PANOS_LAB_USERNAME', 'PANOS_PASSWORD'])
def test_lab_instance_names_missing_variable_only(monkeypatch, missing):
    values = dict(STATIC_ENV)
    values.pop(missing)
    with pytest.raises(pytest.fail.Exception) as error:
        build_lab_instance(values)
    assert missing in str(error.value)
    assert PASSWORD not in str(error.value)


@pytest.mark.parametrize(
    'collect_all, expected',
    [('', False), ('0', False), ('false', False), ('no', False), ('1', True), ('true', True), ('True', True)],
)
def test_lab_instance_turns_on_optional_collectors_on_request(collect_all, expected):
    instance = build_lab_instance({**STATIC_ENV, 'PANOS_LAB_COLLECT_ALL': collect_all})
    flags = ('collect_global_counters', 'collect_ospf', 'collect_reports')
    assert [instance.get(flag, False) for flag in flags] == [expected] * 3


def test_lab_panorama_instance_is_built_from_the_environment():
    instance = build_lab_instance(PANORAMA_ENV)

    assert instance == {
        'panorama_host': 'panorama.example.com',
        'panorama_username': 'panorama-user',
        'panorama_password': PANORAMA_PASSWORD,
        'firewall_credentials': [{'username': 'lab-user', 'password': PASSWORD}],
        'firewall_ip_overrides': {'007955000930601': '192.0.2.10', '007955000930602': '192.0.2.11'},
        'tls_verify': False,
    }


def test_lab_mode_selects_the_instance_shape():
    # The mode comes from PANOS_LAB_MODE alone: the Panorama host variable of the other mode is ignored.
    static = build_lab_instance({**STATIC_ENV, 'PANOS_LAB_PANORAMA_HOST': 'panorama.example.com'})
    panorama = build_lab_instance({**PANORAMA_ENV, 'PANOS_LAB_HOSTS': '192.0.2.99'})

    assert static['firewalls'] == ['192.0.2.10'] and 'panorama_host' not in static
    assert panorama['panorama_host'] == 'panorama.example.com' and 'firewalls' not in panorama


@pytest.mark.parametrize('mode', [None, '', 'Static', 'both'])
def test_lab_instance_rejects_an_unknown_mode_naming_the_variable(mode):
    environ = (
        {**STATIC_ENV, 'PANOS_LAB_MODE': mode}
        if mode is not None
        else {k: v for k, v in STATIC_ENV.items() if k != 'PANOS_LAB_MODE'}
    )
    with pytest.raises(pytest.fail.Exception) as error:
        build_lab_instance(environ)
    message = str(error.value)
    assert 'PANOS_LAB_MODE' in message and 'static' in message and 'panorama' in message
    assert PASSWORD not in message


def test_lab_panorama_overrides_are_optional():
    environ = {k: v for k, v in PANORAMA_ENV.items() if k != 'PANOS_LAB_FIREWALL_OVERRIDES'}

    assert 'firewall_ip_overrides' not in build_lab_instance(environ)


def test_lab_panorama_instance_turns_on_optional_collectors_on_request():
    instance = build_lab_instance({**PANORAMA_ENV, 'PANOS_LAB_COLLECT_ALL': '1'})

    assert [instance.get(f) for f in ('collect_global_counters', 'collect_ospf', 'collect_reports')] == [True] * 3


@pytest.mark.parametrize(
    'missing',
    ['PANOS_LAB_PANORAMA_USERNAME', 'PANOS_LAB_PANORAMA_PASSWORD', 'PANOS_LAB_USERNAME', 'PANOS_PASSWORD'],
)
def test_lab_panorama_instance_names_missing_variable_only(missing):
    environ = {k: v for k, v in PANORAMA_ENV.items() if k != missing}
    with pytest.raises(pytest.fail.Exception) as error:
        build_lab_instance(environ)
    message = str(error.value)
    assert missing in message
    assert [v for v in PANORAMA_ENV.values() if v in message] == []


@pytest.mark.parametrize(
    'overrides',
    ['007955000930601', '007955000930601=', '=192.0.2.10', '007955000930601=not-an-ip', '007955000930601=192.0.2.10=x'],
)
def test_lab_panorama_malformed_overrides_name_the_variable_only(overrides):
    with pytest.raises(pytest.fail.Exception) as error:
        build_lab_instance({**PANORAMA_ENV, 'PANOS_LAB_FIREWALL_OVERRIDES': overrides})
    message = str(error.value)
    assert 'PANOS_LAB_FIREWALL_OVERRIDES' in message
    assert overrides not in message


@pytest.mark.parametrize(
    'subnet, firewalls, panorama',
    [
        ('172.29.84.0/24', {'fw-a': '172.29.84.10', 'fw-b': '172.29.84.11'}, '172.29.84.12'),
        ('10.99.4.0/24', {'fw-a': '10.99.4.10', 'fw-b': '10.99.4.11'}, '10.99.4.12'),
        ('10.99.4.7/24', {'fw-a': '10.99.4.10', 'fw-b': '10.99.4.11'}, '10.99.4.12'),
    ],
)
def test_e2e_addresses_follow_the_subnet(subnet, firewalls, panorama):
    assert e2e_addresses(subnet) == (firewalls, panorama)


@pytest.mark.parametrize('subnet', ['10.99.4.0/29', 'fd00::/64', 'not-a-subnet'])
def test_e2e_addresses_reject_a_subnet_that_cannot_hold_the_fakes(subnet):
    with pytest.raises((pytest.fail.Exception, ValueError)):
        e2e_addresses(subnet)
