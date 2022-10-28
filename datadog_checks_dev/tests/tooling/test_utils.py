# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from os.path import join

import mock

from datadog_checks.dev.tooling.config import copy_default_config
from datadog_checks.dev.tooling.utils import (
    complete_set_root,
    get_check_files,
    get_version_string,
    has_process_signature,
    initialize_root,
    is_logs_only,
    parse_agent_req_file,
)

from ..common import not_windows_ci

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../..'))


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
def test_is_logs_only(get_root):
    get_root.return_value = REPO_ROOT
    assert is_logs_only('flink')


@mock.patch('datadog_checks.dev.tooling.utils.get_root')
def test_has_process_signature(get_root):
    get_root.return_value = REPO_ROOT
    assert has_process_signature('rethinkdb')


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


@mock.patch('datadog_checks.dev.tooling.utils.get_root')
def test_get_check_files(get_root):
    get_root.return_value = ''

    mock_dir_map = {
        '': [
            (
                'dns_check',
                ['datadog_checks', 'datadog_dns_check.egg-info', 'tests', '.junit', 'assets'],
                [
                    'CHANGELOG.md',
                    'MANIFEST.in',
                    'setup.py',
                    'requirements-dev.txt',
                    'tox.ini',
                    'manifest.json',
                    'metadata.csv',
                ],
            )
        ],
        'datadog_checks': [
            (join('dns_check', 'datadog_checks'), ['dns_check'], ['__init__.py']),
            (
                join('dns_check', 'datadog_checks', 'dns_check'),
                ['data'],
                ['__init__.py', '__about__.py', 'dns_check.py'],
            ),
            (join('dns_check', 'datadog_checks', 'dns_check', 'data'), [], ['conf.yaml.example']),
        ],
        '.tox': [(join('dns_check', '.tox'), ['py37', '.tmp', 'py27'], [])],
        'datadog_dns_check.egg-info': [
            (join('dns_check', 'datadog_dns_check.egg-info'), [], ['PKG-INFO', 'SOURCES.txt'])
        ],
        'tests': [(join('dns_check', 'tests'), [], ['test_dns_check.py', '__init__.py', 'common.py'])],
        '.junit': [(join('dns_check', '.junit'), [], ['test-e2e-py37.xml', 'test-e2e-py27.xml'])],
        'assets': [(join('dns_check', 'assets'), [], ['service_checks.json'])],
    }

    default_py_files = [
        join('dns_check', 'datadog_checks', '__init__.py'),
        join('dns_check', 'datadog_checks', 'dns_check', '__init__.py'),
        join('dns_check', 'datadog_checks', 'dns_check', '__about__.py'),
        join('dns_check', 'datadog_checks', 'dns_check', 'dns_check.py'),
        join('dns_check', 'tests', 'test_dns_check.py'),
        join('dns_check', 'tests', '__init__.py'),
        join('dns_check', 'tests', 'common.py'),
    ]

    with mock.patch('os.walk') as mockwalk:
        mockwalk.side_effect = lambda base: mock_dir_map[os.path.basename(base)]

        files = get_check_files('dns_check')
        assert list(files) == default_py_files

        files = get_check_files('dns_check', file_suffix='.json', include_dirs=['assets'])
        assert list(files) == [join('dns_check', 'assets', 'service_checks.json')]

        files = get_check_files('dns_check', file_suffix='.json', include_dirs=['', 'assets'])
        assert list(files) == [join('dns_check', 'manifest.json'), join('dns_check', 'assets', 'service_checks.json')]
