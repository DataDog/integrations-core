# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import mock

from datadog_checks.http_check import HTTPCheck, http_check


def test__init__():
    # empty values should be ignored
    init_config = {'ca_certs': ''}
    # `get_ca_certs_path` needs to be mocked because it's used as fallback when
    # init_config doesn't contain `ca_certs`
    with mock.patch('datadog_checks.http_check.http_check.get_ca_certs_path', return_value='bar'):
        http_check = HTTPCheck('http_check', init_config, [{}])
        assert http_check.ca_certs == 'bar'

    # normal case
    init_config = {'ca_certs': 'foo'}
    http_check = HTTPCheck('http_check', init_config, [{}])
    assert http_check.ca_certs == 'foo'


def test_instances_do_not_share_data():
    http_check_1 = HTTPCheck('http_check', {'ca_certs': 'foo'}, [{}])
    http_check_1.HTTP_CONFIG_REMAPPER['ca_certs']['default'] = 'foo'
    http_check_2 = HTTPCheck('http_check', {'ca_certs': 'bar'}, [{}])
    http_check_2.HTTP_CONFIG_REMAPPER['ca_certs']['default'] = 'bar'

    assert http_check_1.HTTP_CONFIG_REMAPPER['ca_certs']['default'] == 'foo'
    assert http_check_2.HTTP_CONFIG_REMAPPER['ca_certs']['default'] == 'bar'


def test_message_lenght_when_content_is_too_long():
    max_lenght = http_check.MESSAGE_LENGTH
    try:
        http_check.MESSAGE_LENGTH = 25
        too_long_content = 'this message is too long'
        error_message = 'There has been an error.'
        message = HTTPCheck._include_content(True, error_message, too_long_content)
    finally:
        http_check.MESSAGE_LENGTH = max_lenght

    assert len(message) == 25
    assert error_message in message
    assert too_long_content not in message


def test_message_lenght_when_content_is_ok():
    content = '''{
    "HikariPool-1.pool.ConnectivityCheck" : {
        "healthy" : true
    },
    "database" : {
        "healthy" : true,
        "message" : "Service located at jdbc ostgresql://pgbouncer-server.staging.net is alive. Version: 1.5"
    },
    "deadlocks" : {
        "healthy" : true
    }
    "gateway" : {
        "healthy" : true,
        "message" : "Service located at https://apis.staging.eu.people-doc.com is alive."
    }
}'''
    error_message = 'There has been an error.'
    message = HTTPCheck._include_content(True, error_message, content)

    assert len(message) < http_check.MESSAGE_LENGTH
    assert content in message
    assert error_message in message


def test_message_when_content_is_disabled():
    content = "This is not part of the message"
    error_message = 'There has been an error.'
    message = HTTPCheck._include_content(False, error_message, content)

    assert message == error_message
    assert content not in message
