# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import pytest

from datadog_checks.oracle import Oracle

from .common import CHECK_NAME


def test__get_config(check, instance):
    """
    Test the _get_config method
    """
    check = Oracle(CHECK_NAME, {}, [instance])

    assert check._user == 'system'
    assert check._password == 'oracle'
    assert check._service == 'xe'
    assert check._jdbc_driver is None
    assert check._tags == ['optional:tag1']
    assert check._service_check_tags == ['server:{}'.format(instance['server']), 'optional:tag1']
    assert len(check._query_manager.queries) == 3


def test_check_misconfig_null_server(dd_run_check, instance):
    """
    Test null server
    """
    instance['server'] = None
    check = Oracle(CHECK_NAME, {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)


def test_check_misconfig_invalid_protocol(dd_run_check, instance):
    """
    Test invalid protocol
    """
    instance['protocol'] = 'TCPP'
    check = Oracle(CHECK_NAME, {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)


def test_check_misconfig_empty_truststore_and_type(dd_run_check, instance):
    """
    Test if connecting via JDBC with TCPS, both `jdbc_truststore` and `jdbc_truststore_type` are non-empty
    """
    instance['jdbc_driver_path'] = '/path/to/jdbc/driver'
    instance['jdbc_truststore_path'] = ''
    instance['jdbc_truststore_type'] = 'SSO'
    instance['protocol'] = 'TCPS'

    check = Oracle(CHECK_NAME, {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)


def test_check_misconfig_invalid_truststore_type(dd_run_check, instance):
    """
    Test truststore type is valid
    """
    instance['jdbc_driver_path'] = '/path/to/jdbc/driver'
    instance['jdbc_truststore_path'] = '/path/to/jdbc/truststore'
    instance['jdbc_truststore_type'] = 'wrong_type'
    instance['protocol'] = 'TCPS'
    check = Oracle(CHECK_NAME, {}, [instance])
    with pytest.raises(Exception):
        dd_run_check(check)
