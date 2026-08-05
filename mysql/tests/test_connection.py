# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import copy

import pytest

from datadog_checks.mysql import MySql

from . import common

pytestmark = pytest.mark.unit


def test_connection_with_defaults_file():
    file_instance = {
        'host': 'localhost',
        'port': '123',
        'user': 'ddog',
        'defaults_file': '/foo/bar',
    }
    check = MySql(common.CHECK_NAME, {}, [file_instance])
    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': 10,
        'read_default_file': '/foo/bar',
    }
    assert 'host' not in connection_args


def test_connection_with_sock():
    file_instance = {
        'host': 'localhost',
        'port': '123',
        'user': 'ddog',
        'pass': 'pwd',
        'sock': '/foo/bar',
    }
    check = MySql(common.CHECK_NAME, {}, [file_instance])
    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': 10,
        'unix_socket': '/foo/bar',
        'user': 'ddog',
        'passwd': 'pwd',
        'port': 123,
    }


def test_connection_with_host():
    file_instance = {
        'host': 'localhost',
        'user': 'ddog',
        'pass': 'pwd',
    }
    check = MySql(common.CHECK_NAME, {}, [file_instance])
    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': 10,
        'user': 'ddog',
        'passwd': 'pwd',
        'host': 'localhost',
    }


def test_connection_with_host_and_port():
    file_instance = {'host': 'localhost', 'user': 'ddog', 'pass': 'pwd', 'port': '123'}
    check = MySql(common.CHECK_NAME, {}, [file_instance])
    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': 10,
        'user': 'ddog',
        'passwd': 'pwd',
        'host': 'localhost',
        'port': 123,
    }


def test_connection_with_charset(instance_basic):
    instance = copy.deepcopy(instance_basic)
    instance['charset'] = 'utf8mb4'
    check = MySql(common.CHECK_NAME, {}, [instance])

    connection_args = check._get_connection_args()
    assert connection_args == {
        'autocommit': True,
        'host': common.HOST,
        'user': common.USER,
        'passwd': common.PASS,
        'port': common.PORT,
        'ssl': None,
        'connect_timeout': 10,
        'read_timeout': 10,
        'charset': 'utf8mb4',
    }
