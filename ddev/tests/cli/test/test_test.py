# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import sys

import pytest

from ddev.repo.core import Repository
from ddev.utils.structures import EnvVars


class TestInputValidation:
    @pytest.mark.parametrize('flag', ('--lint', '--fmt', '--bench', '--latest'))
    def test_specific_environment_and_functionality(self, ddev, helpers, flag):
        result = ddev('test', 'postgres:foo', flag)

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Cannot specify environments when using specific functionality like linting
            """
        )

    def test_unknown_target(self, ddev, helpers):
        result = ddev('test', 'foo')

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Unknown target: foo
            """
        )

    def test_target_not_testable(self, ddev, helpers):
        result = ddev('test', 'datadog_checks_dependency_provider')

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            No testable targets found
            """
        )


class TestListEnvironments:
    def test_single_target(self, ddev, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        result = ddev('test', 'postgres', '--list')

        assert result.exit_code == 0, result.output
        assert not result.output

        assert run.call_args_list == [
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'show'], shell=False),
        ]

    def test_multiple_targets(self, ddev, helpers, mocker):
        changed_files = ['nginx/pyproject.toml', 'win32_event_log/pyproject.toml']
        changed_file_processes = helpers.changed_file_processes(changed_files)
        run = mocker.patch(
            'subprocess.run',
            side_effect=[*changed_file_processes, *[mocker.MagicMock(returncode=0)] * len(changed_files)],
        )

        result = ddev('test', '--list')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ──────────────────────────────────── NGINX ─────────────────────────────────────
            ────────────────────────────── Windows Event Log ───────────────────────────────
            """
        )

        assert run.call_args_list[len(changed_file_processes) :] == [
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'show'], shell=False),
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'show'], shell=False),
        ]


class TestStandard:
    def test_all_environments(self, ddev, helpers, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        result = ddev('test', 'win32_event_log')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ────────────────────────────── Windows Event Log ───────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test', '--tb', 'short'],
                shell=False,
            )
        ]

    def test_specific_environments(self, ddev, helpers, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        result = ddev('test', 'win32_event_log:foo,bar')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ────────────────────────────── Windows Event Log ───────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--env',
                    'foo',
                    '--env',
                    'bar',
                    '--',
                    'test',
                    '--tb',
                    'short',
                ],
                shell=False,
            )
        ]

    def test_changed_target_detection(self, ddev, helpers, mocker):
        changed_files = ['nginx/pyproject.toml', 'win32_event_log/pyproject.toml']
        changed_file_processes = helpers.changed_file_processes(changed_files)
        run = mocker.patch(
            'subprocess.run',
            side_effect=[*changed_file_processes, *[mocker.MagicMock(returncode=0)] * len(changed_files)],
        )

        result = ddev('test')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ──────────────────────────────────── NGINX ─────────────────────────────────────
            ────────────────────────────── Windows Event Log ───────────────────────────────
            """
        )

        assert run.call_args_list[len(changed_file_processes) :] == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test', '--tb', 'short'],
                shell=False,
            ),
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test', '--tb', 'short'],
                shell=False,
            ),
        ]

    def test_changed_no_modifications(self, ddev, helpers, mocker):
        mocker.patch('subprocess.run')
        result = ddev('test')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            No changed testable targets found
            """
        )

    def test_all_targets(self, ddev, helpers, mocker, repository):
        repo = Repository("core", str(repository.path))
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        result = ddev('test', 'all')

        assert result.exit_code == 0, result.output

        assert run.call_args_list == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test', '--tb', 'short'],
                shell=False,
            )
            for _ in repo.integrations.iter_testable('all')
        ]

    def test_argument_forwarding(self, ddev, helpers, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        result = ddev('test', 'win32_event_log', 'foo', 'bar')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ────────────────────────────── Windows Event Log ───────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--ignore-compat',
                    '--',
                    'test',
                    '--tb',
                    'short',
                    'foo',
                    'bar',
                ],
                shell=False,
            )
        ]

    @pytest.mark.parametrize(
        'flag, hatch_verbose, hatch_quiet',
        [
            pytest.param('-v', ('HATCH_VERBOSE', '2'), ('HATCH_QUIET', None), id='extra verbose'),
            pytest.param('-qv', ('HATCH_VERBOSE', '1'), ('HATCH_QUIET', None), id='default verbose'),
            pytest.param('-q', ('HATCH_VERBOSE', None), ('HATCH_QUIET', None), id='verbosity off'),
            pytest.param('-qq', ('HATCH_VERBOSE', None), ('HATCH_QUIET', '1'), id='quiet'),
        ],
    )
    def test_verbosity(self, ddev, helpers, mocker, flag, hatch_verbose, hatch_quiet):
        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        result = ddev(flag, 'test', 'win32_event_log')

        expected_command = [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test']

        assert result.exit_code == 0, result.output
        if flag.startswith('-v'):
            assert result.output == helpers.dedent(
                f"""
                DEBUG: Targets: win32_event_log
                ────────────────────────────── Windows Event Log ───────────────────────────────
                DEBUG: Command: {expected_command!r}
                """
            )
        else:
            expected_command.extend(('--tb', 'short'))
            assert result.output == helpers.dedent(
                """
                ────────────────────────────── Windows Event Log ───────────────────────────────
                """
            )

        assert run.call_args_list == [mocker.call(expected_command, shell=False)]

        verbose_env_var, verbose_value = hatch_verbose
        if verbose_value is None:
            assert verbose_env_var not in env_vars
        else:
            assert env_vars[verbose_env_var] == verbose_value

        quiet_env_var, quiet_value = hatch_quiet
        if quiet_value is None:
            assert quiet_env_var not in env_vars
        else:
            assert env_vars[quiet_env_var] == quiet_value

    def test_api_key(self, ddev, config_file, helpers, mocker):
        config_file.model.orgs['default']['api_key'] = 'foo'
        config_file.save()

        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        with EnvVars({'DD_API_KEY': 'bar'}):
            result = ddev('test', 'win32_event_log')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ────────────────────────────── Windows Event Log ───────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test', '--tb', 'short'],
                shell=False,
            )
        ]
        assert env_vars['DD_API_KEY'] == 'foo'

    def test_python_filter(self, ddev, helpers, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        with EnvVars({'PYTHON_FILTER': '3.9'}):
            result = ddev('test', 'win32_event_log')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ────────────────────────────── Windows Event Log ───────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--ignore-compat',
                    '--filter',
                    '{"python": "3.9"}',
                    '--',
                    'test',
                    '--tb',
                    'short',
                ],
                shell=False,
            )
        ]


class TestSpecificFunctionality:
    @pytest.mark.parametrize('flag', ('--lint', '-s'))
    def test_lint(self, ddev, config_file, helpers, mocker, flag):
        config_file.model.orgs['default']['api_key'] = 'foo'
        config_file.save()

        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        with EnvVars({'DD_API_KEY': 'bar'}):
            result = ddev('test', 'postgres', flag)

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--env', 'lint', '--', 'all'],
                shell=False,
            )
        ]
        assert env_vars['DD_API_KEY'] == 'bar'

    @pytest.mark.parametrize('flag', ('--fmt', '-fs'))
    def test_fmt(self, ddev, config_file, helpers, mocker, flag):
        config_file.model.orgs['default']['api_key'] = 'foo'
        config_file.save()

        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        with EnvVars({'DD_API_KEY': 'bar'}):
            result = ddev('test', 'postgres', flag)

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--env', 'lint', '--', 'fmt'],
                shell=False,
            )
        ]
        assert env_vars['DD_API_KEY'] == 'bar'

    @pytest.mark.parametrize('flag', ('--bench', '-b'))
    def test_bench(self, ddev, config_file, helpers, mocker, flag):
        config_file.model.orgs['default']['api_key'] = 'foo'
        config_file.save()

        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        with EnvVars({'DD_API_KEY': 'bar'}):
            result = ddev('test', 'postgres', flag)

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--filter', '{"benchmark-env": true}', '--', 'benchmark'],
                shell=False,
            )
        ]
        assert env_vars['DD_API_KEY'] == 'foo'

    def test_latest(self, ddev, config_file, helpers, mocker):
        config_file.model.orgs['default']['api_key'] = 'foo'
        config_file.save()

        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        with EnvVars({'DD_API_KEY': 'bar'}):
            result = ddev('test', 'clickhouse', '--latest')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ────────────────────────────────── ClickHouse ──────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--filter',
                    '{"latest-env": true}',
                    '--',
                    'test',
                    '--run-latest-metrics',
                ],
                shell=False,
            )
        ]
        assert env_vars['DD_API_KEY'] == 'foo'


class TestCoverage:
    def test_local(self, ddev, helpers, mocker, repository):
        run = mocker.patch('subprocess.run', side_effect=[mocker.MagicMock(returncode=0)] * 2)
        coverage_file = repository.path / 'postgres' / '.coverage'
        coverage_file.touch()

        with EnvVars({'GITHUB_ACTIONS': 'false', 'CI': 'false'}):
            result = ddev('test', 'postgres', '--cov')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            ─────────────────────────────── Coverage report ────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test-cov', '--tb', 'short'],
                shell=False,
            ),
            mocker.call([sys.executable, '-m', 'coverage', 'report', '--rcfile=../.coveragerc'], shell=False),
        ]
        assert not coverage_file.exists()

    def test_ci(self, ddev, helpers, mocker, repository):
        run = mocker.patch('subprocess.run', side_effect=[mocker.MagicMock(returncode=0)] * 3)
        coverage_file = repository.path / 'postgres' / 'coverage.xml'
        coverage_file.write_text(
            helpers.dedent(
                """
                <?xml version="1.0" ?>
                <coverage version="6.5.0" ...>
                    <!-- Generated by coverage.py: https://coverage.readthedocs.io -->
                    <!-- Based on https://raw.githubusercontent.com/cobertura/web/master/htdocs/xml/coverage-04.dtd -->
                    <sources>
                        <source>/</source>
                    </sources>
                    <packages>
                        <package name="tests" ...>
                            <classes>
                                <class name="conftest.py" filename="tests/conftest.py" ...>
                                    <methods/>
                """
            )
        )

        with EnvVars({'GITHUB_ACTIONS': 'true'}):
            result = ddev('test', 'postgres', '--cov')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            ─────────────────────────────── Coverage report ────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test-cov', '--tb', 'short'],
                shell=False,
            ),
            mocker.call([sys.executable, '-m', 'coverage', 'report', '--rcfile=../.coveragerc'], shell=False),
            mocker.call([sys.executable, '-m', 'coverage', 'xml', '-i', '--rcfile=../.coveragerc'], shell=False),
        ]
        assert coverage_file.read_text() == helpers.dedent(
            """
            <?xml version="1.0" ?>
            <coverage version="6.5.0" ...>
                <!-- Generated by coverage.py: https://coverage.readthedocs.io -->
                <!-- Based on https://raw.githubusercontent.com/cobertura/web/master/htdocs/xml/coverage-04.dtd -->
                <sources>
                    <source>/</source>
                </sources>
                <packages>
                    <package name="tests" ...>
                        <classes>
                            <class name="conftest.py" filename="postgres/tests/conftest.py" ...>
                                <methods/>
            """
        )


class TestJUnit:
    def test_unit(self, ddev, helpers, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        result = ddev('test', 'postgres', '--junit')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--ignore-compat',
                    '--',
                    'test',
                    '--tb',
                    'short',
                    '--junit-xml',
                    '.junit/test-unit-$HATCH_ENV_ACTIVE.xml',
                    '--junit-prefix',
                    'postgres',
                ],
                shell=False,
            )
        ]

    def test_e2e(self, ddev, helpers, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        result = ddev('test', 'postgres', '--junit', '--e2e')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--ignore-compat',
                    '--',
                    'test',
                    '--tb',
                    'short',
                    '-m',
                    'e2e',
                    '--junit-xml',
                    '.junit/test-e2e-$HATCH_ENV_ACTIVE.xml',
                    '--junit-prefix',
                    'postgres',
                ],
                shell=False,
            )
        ]


class TestDDTrace:
    @pytest.mark.requires_unix
    def test_default(self, ddev, helpers, mocker):
        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        result = ddev('test', 'postgres', '--ddtrace')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--ignore-compat',
                    '--',
                    'test',
                    '--tb',
                    'short',
                    '--ddtrace',
                ],
                shell=False,
            )
        ]
        assert env_vars['DDEV_TRACE_ENABLED'] == 'true'
        assert env_vars['DD_PROFILING_ENABLED'] == 'true'
        assert env_vars['DD_SERVICE'] == 'ddev-integrations'
        assert env_vars['DD_ENV'] == 'ddev-integrations'

    @pytest.mark.requires_unix
    def test_specific_tags(self, ddev, helpers, mocker):
        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        with EnvVars({'DD_SERVICE': 'foo', 'DD_ENV': 'bar'}):
            result = ddev('test', 'postgres', '--ddtrace')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--ignore-compat',
                    '--',
                    'test',
                    '--tb',
                    'short',
                    '--ddtrace',
                ],
                shell=False,
            )
        ]
        assert env_vars['DDEV_TRACE_ENABLED'] == 'true'
        assert env_vars['DD_PROFILING_ENABLED'] == 'true'
        assert env_vars['DD_SERVICE'] == 'foo'
        assert env_vars['DD_ENV'] == 'bar'

    @pytest.mark.requires_windows
    def test_windows_only_python3(self, ddev, helpers, mocker):
        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        result = ddev('test', 'postgres:py3.11', '--ddtrace')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--env',
                    'py3.11',
                    '--',
                    'test',
                    '--tb',
                    'short',
                    '--ddtrace',
                ],
                shell=False,
            )
        ]
        assert env_vars['DDEV_TRACE_ENABLED'] == 'true'
        assert env_vars['DD_PROFILING_ENABLED'] == 'true'
        assert env_vars['DD_SERVICE'] == 'ddev-integrations'
        assert env_vars['DD_ENV'] == 'ddev-integrations'

    @pytest.mark.requires_windows
    def test_windows_possible_python2(self, ddev, helpers, mocker):
        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        result = ddev('test', 'postgres', '--ddtrace')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            Tracing is only supported on Python 3 on Windows
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--ignore-compat',
                    '--',
                    'test',
                    '--tb',
                    'short',
                ],
                shell=False,
            )
        ]
        assert 'DD_SERVICE' not in env_vars
        assert 'DD_ENV' not in env_vars


class TestMemray:
    @pytest.mark.requires_unix
    def test_unix(self, ddev, helpers, mocker):
        run = mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        result = ddev('test', 'postgres', '--memray')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--ignore-compat',
                    '--',
                    'test',
                    '--tb',
                    'short',
                    '--memray',
                ],
                shell=False,
            )
        ]

    @pytest.mark.requires_windows
    def test_windows(self, ddev, helpers, mocker):
        mocker.patch('subprocess.run', return_value=mocker.MagicMock(returncode=0))

        result = ddev('test', 'postgres', '--memray')

        assert result.exit_code == 1, result.output
        assert result.output == helpers.dedent(
            """
            Memory profiling with `memray` is not supported on Windows
            """
        )


class TestRecreate:
    def test_bench(self, ddev, helpers, mocker):
        mocker.patch(
            'ddev.utils.platform.Platform.check_command_output',
            return_value=json.dumps({'foo': {'benchmark-env': True}, 'bar': {}, 'baz': {'benchmark-env': True}}),
        )
        run = mocker.patch('subprocess.run', side_effect=[mocker.MagicMock(returncode=0)] * 3)

        result = ddev('test', 'postgres', '--bench', '--recreate')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'remove', 'foo'], shell=False),
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'remove', 'baz'], shell=False),
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--filter', '{"benchmark-env": true}', '--', 'benchmark'],
                shell=False,
            ),
        ]

    def test_latest(self, ddev, helpers, mocker):
        mocker.patch(
            'ddev.utils.platform.Platform.check_command_output',
            return_value=json.dumps({'foo': {'latest-env': True}, 'bar': {}, 'baz': {'latest-env': True}}),
        )
        run = mocker.patch('subprocess.run', side_effect=[mocker.MagicMock(returncode=0)] * 3)

        result = ddev('test', 'postgres', '--latest', '--recreate')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'remove', 'foo'], shell=False),
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'remove', 'baz'], shell=False),
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--filter',
                    '{"latest-env": true}',
                    '--',
                    'test',
                    '--run-latest-metrics',
                ],
                shell=False,
            ),
        ]

    def test_specific_environments(self, ddev, helpers, mocker):
        run = mocker.patch('subprocess.run', side_effect=[mocker.MagicMock(returncode=0)] * 3)

        result = ddev('test', 'postgres:foo,bar', '--recreate')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'remove', 'foo'], shell=False),
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'remove', 'bar'], shell=False),
            mocker.call(
                [
                    sys.executable,
                    '-m',
                    'hatch',
                    'env',
                    'run',
                    '--env',
                    'foo',
                    '--env',
                    'bar',
                    '--',
                    'test',
                    '--tb',
                    'short',
                ],
                shell=False,
            ),
        ]

    def test_all_environments(self, ddev, helpers, mocker):
        run = mocker.patch('subprocess.run', side_effect=[mocker.MagicMock(returncode=0)] * 2)

        result = ddev('test', 'postgres', '--recreate')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call([sys.executable, '-m', 'hatch', 'env', 'remove', 'default'], shell=False),
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test', '--tb', 'short'],
                shell=False,
            ),
        ]


class TestPluginInteraction:
    def test_minimum_base_package_version(self, ddev, helpers, mocker, repository):
        import tomlkit

        env_vars = {}
        run = mocker.patch(
            'subprocess.run',
            side_effect=lambda *args, **kwargs: env_vars.update(os.environ) or mocker.MagicMock(returncode=0),
        )

        project_file = repository.path / 'postgres' / 'pyproject.toml'
        data = tomlkit.parse(project_file.read_text())
        data['project']['dependencies'] = ['datadog-checks-base>=9000,<10000']
        project_file.write_text(tomlkit.dumps(data))

        result = ddev('test', 'postgres', '--compat')

        assert result.exit_code == 0, result.output
        assert result.output == helpers.dedent(
            """
            ─────────────────────────────────── Postgres ───────────────────────────────────
            """
        )

        assert run.call_args_list == [
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'remove', 'default'],
                shell=False,
            ),
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'run', '--ignore-compat', '--', 'test', '--tb', 'short'],
                shell=False,
            ),
            mocker.call(
                [sys.executable, '-m', 'hatch', 'env', 'remove', 'default'],
                shell=False,
            ),
        ]
        assert env_vars['DDEV_TEST_BASE_PACKAGE_VERSION'] == '9000'
