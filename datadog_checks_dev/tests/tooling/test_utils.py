# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import mock

from datadog_checks.dev.tooling.config import copy_default_config
from datadog_checks.dev.tooling.utils import (
    complete_set_root,
    get_version_string,
    initialize_root,
    parse_agent_req_file,
)

from ..common import not_windows_ci


def test_parse_agent_req_file():
    contents = "datadog-active-directory==1.1.1; sys_platform == 'win32'\nthis is garbage"
    catalog = parse_agent_req_file(contents)
    assert len(catalog) == 1
    assert catalog['datadog-active-directory'] == '1.1.1'


def test_get_version_string():
    with mock.patch('datadog_checks.dev.tooling.utils.read_version_file') as read:
        read.return_value = '__version__ = "2.0.0"'
        assert get_version_string('foo_check') == '2.0.0'


@mock.patch('datadog_checks.dev.tooling.utils.get_root')
@mock.patch('datadog_checks.dev.tooling.utils.set_root')
def test_initialize_root_bad_path(set_root, get_root):
    get_root.return_value = ''

    # bad path in config results in cwd
    config = copy_default_config()
    config['core'] = '/path/does/not/exist'
    initialize_root(config)
    assert set_root.called
    set_root.assert_called_with(os.getcwd())


@mock.patch('datadog_checks.dev.tooling.utils.get_root')
@mock.patch('datadog_checks.dev.tooling.utils.set_root')
def test_initialize_root_good_path(set_root, get_root):
    get_root.return_value = ''

    # good path in config uses that
    config = copy_default_config()
    config['core'] = '~'
    initialize_root(config)
    assert set_root.called
    set_root.assert_called_with(os.path.expanduser('~'))


@not_windows_ci
@mock.patch('datadog_checks.dev.tooling.utils.get_root')
@mock.patch('datadog_checks.dev.tooling.utils.set_root')
def test_initialize_root_env_var(set_root, get_root):
    get_root.return_value = ''

    ddev_env = '/tmp'
    with mock.patch.dict(os.environ, {'DDEV_ROOT': ddev_env}):
        config = copy_default_config()
        initialize_root(config)
        assert set_root.called
        set_root.assert_called_with(os.path.expanduser(ddev_env))


@not_windows_ci
@mock.patch('datadog_checks.dev.tooling.utils.get_root')
@mock.patch('datadog_checks.dev.tooling.utils.set_root')
def test_complete_set_root_no_args(set_root, get_root):
    get_root.return_value = ''

    with mock.patch('datadog_checks.dev.tooling.utils.load_config') as load_config:
        config = copy_default_config()
        config['core'] = '/tmp'  # ensure we choose a dir that exists
        load_config.return_value = config

        args = []
        complete_set_root(args)
        assert set_root.called
        set_root.assert_called_with(config['core'])


@mock.patch('datadog_checks.dev.tooling.utils.get_root')
@mock.patch('datadog_checks.dev.tooling.utils.set_root')
def test_complete_set_root_here(set_root, get_root):
    get_root.return_value = ''

    with mock.patch('datadog_checks.dev.tooling.utils.load_config') as load_config:
        config = copy_default_config()
        load_config.return_value = config

        args = ['-x']
        complete_set_root(args)
        assert set_root.called
        set_root.assert_called_with(os.getcwd())


@not_windows_ci
@mock.patch('datadog_checks.dev.tooling.utils.get_root')
@mock.patch('datadog_checks.dev.tooling.utils.set_root')
def test_complete_set_root_extras(set_root, get_root):
    get_root.return_value = ''

    with mock.patch('datadog_checks.dev.tooling.utils.load_config') as load_config:
        config = copy_default_config()
        config['extras'] = '/tmp'  # ensure we choose a dir that exists
        load_config.return_value = config

        args = ['-e']
        complete_set_root(args)
        assert set_root.called
        set_root.assert_called_with(config['extras'])
