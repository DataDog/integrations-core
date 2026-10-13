# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging

import pytest

from .common import build_lab_instance
from .test_check import new_check

PASSWORD = 'lab-password-must-not-leak'


def test_lab_password_never_leaks(monkeypatch, caplog, aggregator):
    monkeypatch.setenv('PANOS_LAB_HOSTS', '192.0.2.10')
    monkeypatch.setenv('PANOS_LAB_USERNAME', 'lab-user')
    monkeypatch.setenv('PANOS_PASSWORD', PASSWORD)
    instance = build_lab_instance()
    assert instance['firewall_credentials'][0]['password'] == PASSWORD

    check = new_check(instance)
    with caplog.at_level(logging.DEBUG):
        check.run()

    # Not `repr(check.config)`: generated pydantic models keep secrets as plain `str`, so it shows the password.
    # That is true of every integration, and the check never logs or prints its config.
    exposed = {'log': caplog.text, 'check': repr(check), 'check str': str(check)}
    assert [name for name, text in exposed.items() if PASSWORD in text] == []


@pytest.mark.parametrize('missing', ['PANOS_LAB_HOSTS', 'PANOS_LAB_USERNAME', 'PANOS_PASSWORD'])
def test_lab_instance_names_missing_variable_only(monkeypatch, missing):
    values = {'PANOS_LAB_HOSTS': '192.0.2.10', 'PANOS_LAB_USERNAME': 'lab-user', 'PANOS_PASSWORD': PASSWORD}
    values.pop(missing)
    with pytest.raises(pytest.fail.Exception) as error:
        build_lab_instance(values)
    assert missing in str(error.value)
    assert PASSWORD not in str(error.value)


@pytest.mark.parametrize('collect_all, expected', [('', False), ('1', True)])
def test_lab_instance_turns_on_optional_collectors_on_request(collect_all, expected):
    values = {'PANOS_LAB_HOSTS': '192.0.2.10', 'PANOS_LAB_USERNAME': 'lab-user', 'PANOS_PASSWORD': PASSWORD}
    instance = build_lab_instance({**values, 'PANOS_LAB_COLLECT_ALL': collect_all})
    flags = ('collect_global_counters', 'collect_ospf', 'collect_reports')
    assert [instance.get(flag, False) for flag in flags] == [expected] * 3
