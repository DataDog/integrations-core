# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture

from ddev.config.file import ConfigFileWithOverrides
from ddev.repo.core import IntegrationRegistry, Repository
from tests.helpers.runner import CliRunner


@pytest.mark.parametrize(
    'args, text',
    [
        (('sample:foo',), 'ddev test sample --envs foo'),
        (('sample', '--', '-m', 'unit'), '--pytest-args'),
        (('sample', 'tests/test_file.py'), '--pytest-args'),
        (('sample', '-k', 'case'), '--pytest-args'),
        (('sample', '--env', 'foo'), '--envs'),
    ],
)
def test_legacy_inputs_have_migration_examples(ddev: CliRunner, commands: MagicMock, args: tuple[str, ...], text: str):
    result = ddev('test', *args)
    assert result.exit_code == 2, result.output
    assert text in result.output
    assert 'postgres' in result.output or 'sample --envs foo' in result.output
    commands.assert_not_called()


@pytest.mark.parametrize('args', [('--envs', 'typo'), ('--envs', 'foo,'), ('--pytest-args', '-m "unit')])
def test_invalid_input_does_not_recreate_environments(
    ddev: CliRunner, commands: MagicMock, mocker: MockerFixture, args: tuple[str, ...]
):
    remove = mocker.patch('ddev.utils.platform.Platform.check_command')
    result = ddev('test', 'sample', '--recreate', *args)
    assert result.exit_code == 2, result.output
    commands.assert_not_called()
    remove.assert_not_called()


@pytest.mark.parametrize(
    'target, message', [('unknown', 'Unknown target: unknown'), ('hatch_only', 'No testable targets')]
)
def test_unavailable_target(ddev: CliRunner, target: str, message: str):
    result = ddev('test', target)
    assert result.exit_code == 1, result.output
    assert message in result.output


def test_explicit_selection_and_pytest_wiring(ddev: CliRunner, commands: MagicMock):
    result = ddev('test', 'sample', '--envs', ' bar,foo,bar ', '--pytest-args', '-m "not flaky" "tests/a file.py"')
    assert result.exit_code == 0, result.output
    assert commands.call_args.args[0] == [
        sys.executable,
        '-m',
        'hatch',
        'env',
        'run',
        '--env',
        'bar',
        '--env',
        'foo',
        '--',
        'test',
        '--tb',
        'short',
        '-m',
        'not flaky',
        'tests/a file.py',
    ]


@pytest.mark.parametrize('args', [(), ('--envs', 'default'), ('--envs', 'default,foo')])
def test_default_matrix_selection(ddev: CliRunner, commands: MagicMock, args: tuple[str, ...]):
    result = ddev('test', 'sample', *args)
    assert result.exit_code == 0, result.output
    assert commands.call_args.args[0] == [
        sys.executable,
        '-m',
        'hatch',
        'env',
        'run',
        '--env',
        'foo',
        '--env',
        'bar',
        '--ignore-compat',
        '--',
        'test',
        '--tb',
        'short',
    ]


@pytest.mark.parametrize('changed', [False, True])
def test_changed_target_detection(
    ddev: CliRunner, commands: MagicMock, test_repo: Repository, mocker: MockerFixture, changed: bool
):
    targets = [test_repo.integrations.get('sample')] if changed else []
    mocker.patch.object(IntegrationRegistry, 'iter_changed', return_value=iter(targets))
    result = ddev('test')
    assert result.exit_code == 0, result.output
    if changed:
        assert commands.call_count == 1
    else:
        commands.assert_not_called()
        assert 'No changed testable targets' in result.output


def test_all_targets_uses_only_testable_integrations(ddev: CliRunner, commands: MagicMock):
    result = ddev('test', 'all')
    assert result.exit_code == 0, result.output
    assert commands.call_count == 1


def test_all_targets_are_validated_before_testing(
    ddev: CliRunner, commands: MagicMock, test_repo: Repository, mocker: MockerFixture
):
    other = test_repo.path / 'other'
    other.mkdir()
    (other / 'hatch.toml').write_text('[env.collectors.datadog-checks]\n')
    (other / 'tests').mkdir()
    result = ddev('test', 'all', '--envs', 'foo')
    assert result.exit_code == 2, result.output
    assert 'Unknown environments: foo' in result.output
    commands.assert_not_called()


@pytest.mark.parametrize(
    'flag, script',
    [
        ('--lint', 'all'),
        ('-s', 'all'),
        ('--lint-unsafe', 'style-unsafe'),
        ('--fmt', 'fmt'),
        ('-fs', 'fmt'),
        ('--fmt-unsafe', 'fmt-unsafe'),
    ],
)
def test_lint_and_format_on_hatch_only_targets(ddev: CliRunner, commands: MagicMock, flag: str, script: str):
    result = ddev('test', 'hatch_only', flag)
    assert result.exit_code == 0, result.output
    assert commands.call_args.args[0] == [
        sys.executable,
        '-m',
        'hatch',
        'env',
        'run',
        '--env',
        'lint',
        '--',
        script,
    ]


@pytest.mark.parametrize('option', [('--envs', 'foo'), ('--pytest-args', '-x')])
def test_lint_rejects_test_inputs(ddev: CliRunner, commands: MagicMock, option: tuple[str, ...]):
    result = ddev('test', 'sample', '--lint', *option)
    assert result.exit_code == 1, result.output
    assert 'Lint and format modes do not accept' in result.output
    commands.assert_not_called()


def test_list_on_hatch_only_targets(ddev: CliRunner, mocker: MockerFixture):
    run = mocker.patch('ddev.utils.platform.Platform.check_command')
    result = ddev('test', 'hatch_only', '--list')
    assert result.exit_code == 0, result.output
    run.assert_called_once_with([sys.executable, '-m', 'hatch', 'env', 'show'])


@pytest.mark.parametrize('mode, script', [('--bench', ['benchmark']), ('--latest', ['test', '--run-latest-metrics'])])
def test_mode_filters_intersect_selection(
    ddev: CliRunner, commands: MagicMock, mocker: MockerFixture, mode: str, script: list[str]
):
    remove = mocker.patch('ddev.utils.platform.Platform.check_command')
    env = 'bench' if mode == '--bench' else 'latest'
    result = ddev('test', 'sample', mode, '--envs', f'foo,{env}', '--recreate')
    assert result.exit_code == 0, result.output
    assert f'Excluded sample:foo by {env if env == "latest" else "benchmark"}-env option.' in result.output
    assert commands.call_args.args[0] == [
        sys.executable,
        '-m',
        'hatch',
        'env',
        'run',
        '--env',
        env,
        '--',
        *script,
    ]
    remove.assert_called_once_with([sys.executable, '-m', 'hatch', 'env', 'remove', env])


def test_empty_python_intersection_skips_execution(ddev: CliRunner, commands: MagicMock):
    result = ddev('test', 'sample', '--envs', 'foo', '--python-filter', '3.12')
    assert result.exit_code == 0, result.output
    assert 'Excluded sample:foo by Python filter 3.12.' in result.output
    assert 'No eligible environments selected for sample.' in result.output
    commands.assert_not_called()


@pytest.mark.parametrize(
    'flags, extra_args, initial_env, env_vars',
    [
        (('--junit',), ['--junit-xml', 'junit/test-unit-$HATCH_ENV_ACTIVE.xml', '--junit-prefix', 'sample'], {}, {}),
        (
            ('--junit', '--e2e'),
            ['--junit-xml', 'junit/test-e2e-$HATCH_ENV_ACTIVE.xml', '--junit-prefix', 'sample', '-m', 'e2e'],
            {},
            {},
        ),
        (('--ddtrace',), ['--ddtrace'], {}, {'DDEV_TRACE_ENABLED': 'true', 'DD_SERVICE': 'ddev-integrations'}),
        (
            ('--ddtrace',),
            ['--ddtrace'],
            {'DD_SERVICE': 'sample-service', 'DD_ENV': 'staging'},
            {'DDEV_TRACE_ENABLED': 'true', 'DD_SERVICE': 'sample-service', 'DD_ENV': 'staging'},
        ),
    ],
)
def test_test_plugins_and_environment(
    ddev: CliRunner,
    commands: MagicMock,
    mocker: MockerFixture,
    flags: tuple[str, ...],
    extra_args: list[str],
    initial_env: dict[str, str],
    env_vars: dict[str, str],
):
    observed = {}
    commands.side_effect = lambda *args, **kwargs: observed.update(os.environ) or ''
    mocker.patch.dict(os.environ, initial_env)
    result = ddev('test', 'sample', '--envs', 'foo', *flags)
    assert result.exit_code == 0, result.output
    assert commands.call_args.args[0][-len(extra_args) :] == extra_args
    assert observed.items() >= env_vars.items()


def test_memory_profiling_support(ddev: CliRunner, commands: MagicMock):
    result = ddev('test', 'sample', '--envs', 'foo', '--memray')
    if sys.platform == 'win32':
        assert result.exit_code == 1, result.output
        assert 'Memory profiling with `memray` is not supported on Windows' in result.output
        commands.assert_not_called()
    else:
        assert result.exit_code == 0, result.output
        assert '--memray' in commands.call_args.args[0]


def test_configured_api_key_takes_precedence(
    ddev: CliRunner, commands: MagicMock, config_file: ConfigFileWithOverrides, mocker: MockerFixture
):
    config_file.model.orgs['default']['api_key'] = 'configured-key'
    config_file.save()
    mocker.patch.dict(os.environ, {'DD_API_KEY': 'ambient-key'})
    observed = {}
    commands.side_effect = lambda *args, **kwargs: observed.update(os.environ) or ''
    result = ddev('test', 'sample', '--envs', 'foo')
    assert result.exit_code == 0, result.output
    assert observed['DD_API_KEY'] == 'configured-key'


def test_e2e_marker_wiring(ddev: CliRunner, commands: MagicMock):
    result = ddev('test', 'sample', '--envs', 'foo', '--e2e', '--pytest-args', '-m "a or b" --markers')
    assert result.exit_code == 0, result.output
    assert commands.call_args.args[0][-3:] == ['-m', '(a or b) and e2e', '--markers']


@pytest.mark.parametrize('flag, verbose, quiet', [('-v', '2', None), ('-qq', None, '1')])
def test_hatch_verbosity(ddev: CliRunner, commands: MagicMock, flag: str, verbose: str | None, quiet: str | None):
    observed = {}
    commands.side_effect = lambda *args, **kwargs: observed.update(os.environ) or ''
    result = ddev(flag, 'test', 'sample')
    assert result.exit_code == 0, result.output
    assert observed.get('HATCH_VERBOSE') == verbose
    assert observed.get('HATCH_QUIET') == quiet


def test_compat_recreates_selected_environments_with_minimum_base(
    ddev: CliRunner, commands: MagicMock, mocker: MockerFixture
):
    observed = {}
    commands.side_effect = lambda *args, **kwargs: observed.update(os.environ) or ''
    remove = mocker.patch('ddev.utils.platform.Platform.check_command')
    result = ddev('test', 'sample', '--compat', '--envs', 'bar')
    assert result.exit_code == 0, result.output
    assert observed['DDEV_TEST_BASE_PACKAGE_VERSION'] == '1.2.3'
    assert [call.args[0] for call in remove.call_args_list] == [
        [sys.executable, '-m', 'hatch', 'env', 'remove', 'bar'],
        [sys.executable, '-m', 'hatch', 'env', 'remove', 'bar'],
    ]


@pytest.mark.parametrize('in_ci', [False, True])
def test_coverage_report(
    ddev: CliRunner, commands: MagicMock, test_repo: Repository, mocker: MockerFixture, in_ci: bool
):
    run = mocker.patch('ddev.utils.platform.Platform.check_command')
    mocker.patch('ddev.utils.ci.running_in_ci', return_value=in_ci)
    path = test_repo.path / 'sample'
    (path / '.coverage').touch()
    (path / 'coverage.xml').write_text('<class filename="tests/test_sample.py"/>')
    result = ddev('test', 'sample', '--cov')
    assert result.exit_code == 0, result.output
    assert 'test-cov' in commands.call_args.args[0]
    assert run.call_args_list[0].args[0] == [sys.executable, '-m', 'coverage', 'report', '--rcfile=../.coveragerc']
    if in_ci:
        assert run.call_args_list[1].args[0] == [
            sys.executable,
            '-m',
            'coverage',
            'xml',
            '-i',
            '--rcfile=../.coveragerc',
        ]
        assert (path / 'coverage.xml').read_text() == '<class filename="sample/tests/test_sample.py"/>'
    else:
        assert not (path / '.coverage').exists()


@pytest.mark.parametrize('flag', ['--lint', '--fmt'])
def test_lint_guidance(ddev: CliRunner, commands: MagicMock, flag: str):
    def failed_lint(command: list[str], **kwargs: Any) -> str:
        kwargs['on_error'](1, '`--unsafe-fixes`')
        return ''

    commands.side_effect = failed_lint
    result = ddev('test', 'sample', flag)
    assert result.exit_code == 0, result.output
    assert 'ddev test --fmt-unsafe' in result.output
