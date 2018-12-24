# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import mock

from datadog_checks.dev.tooling.utils import (
    parse_agent_req_file, get_version_string
)


def test_parse_agent_req_file():
    contents = "datadog-active-directory==1.1.1; sys_platform == 'win32'\nthis is garbage"
    catalog = parse_agent_req_file(contents)
    assert len(catalog) is 1
    assert catalog['datadog-active-directory'] == '1.1.1'


def test_get_version_string():
    with mock.patch('datadog_checks.dev.tooling.utils.read_version_file') as read:
        read.return_value = '__version__ = "2.0.0"'
        assert get_version_string('foo_check') == '2.0.0'
