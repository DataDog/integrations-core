# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
import tomli_w

from ddev.plugin.external.hatch.environment_collector import DatadogChecksEnvironmentCollector


@contextmanager
def argument_file(root: Path, tokens: list[str], *, validate: bool = True) -> Iterator[str]:
    # Only the generated ASCII basename crosses Hatch's formatter and native shell.
    if validate and any(
        character in token for token in tokens for character in '\x00\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029'
    ):
        raise ValueError('Token cannot be represented by a pytest argument-file line')
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', newline='\n', prefix='ddev-args-', suffix='.txt', dir=root, delete=False
    ) as stream:
        path = Path(stream.name)
        for token in tokens:
            stream.write(token + '\n')
    try:
        yield '@' + path.name
    finally:
        path.unlink()


@pytest.mark.skipif(os.environ.get('DDEV_TRANSPORT_PROBE') != '1', reason='Opt-in native-process transport proof')
@pytest.mark.parametrize('transport', os.environ.get('TRANSPORT_KIND', 'response-file,json-adapter').split(','))
def test_literal_pytest_transport(tmp_path: Path, transport: str):
    """Catch token corruption or execution between Hatch's scripts and pytest's parser."""
    root = tmp_path / 'checkout with spaces 雪 {braces}' / 'probe'
    root.mkdir(parents=True)
    tests = root / 'tests'
    tests.mkdir()
    (root.parent / '.coveragerc').write_text('[run]\nbranch = True\n', encoding='utf-8')
    for filename in ('transport_receiver.py', 'transport_entry.py'):
        source = Path(__file__).with_name(filename)
        (root / filename).write_text(source.read_text(encoding='utf-8'), encoding='utf-8')
    (tests / 'test_unit.py').write_text(
        'import pytest\n'
        '@pytest.mark.parametrize("value", ["node with spaces 雪"], ids=["node with spaces 雪"])\n'
        'def test_node(value):\n    assert value\n'
        '@pytest.mark.flaky\ndef test_flaky():\n    assert True\n',
        encoding='utf-8',
    )
    (tests / 'test_e2e.py').write_text(
        'import pytest\ndef test_plain():\n    assert True\n@pytest.mark.flaky\ndef test_flaky():\n    assert True\n',
        encoding='utf-8',
    )
    (tests / 'test_benchmark.py').write_text(
        'def test_bench(benchmark):\n    assert benchmark(lambda: 1) == 1\n',
        encoding='utf-8',
    )
    entry_module = 'transport_entry' if transport == 'json-adapter' else 'pytest'
    unmarked = (
        'subprocess.check_call([sys.executable, "-m", "transport_entry", '
        '"--probe-token=unrelated", "tests/test_unit.py"])\n'
        'pathlib.Path("unrelated.json").write_bytes(pathlib.Path(os.environ["TRANSPORT_RESULT"]).read_bytes())\n'
        if transport == 'json-adapter'
        else ''
    )
    (root / 'forward.py').write_text(
        'import os, pathlib, subprocess, sys\n'
        'pathlib.Path("before").write_text("ran")\n'
        + unmarked
        + f'code = subprocess.call([sys.executable, "-m", {entry_module!r}, *sys.argv[1:]])\n'
        'pathlib.Path("after").write_text("ran")\n'
        'raise SystemExit(code)\n',
        encoding='utf-8',
    )
    (root / 'pytest.ini').write_text(
        '[pytest]\ndisable_test_id_escaping_and_forfeit_all_rights_to_community_support = True\n'
        'markers =\n    flaky: probe selection\n',
        encoding='utf-8',
    )

    configuration = {'default': {}}
    DatadogChecksEnvironmentCollector(root, {}).finalize_config(configuration)
    scripts = configuration['default']['scripts']
    scripts.pop('_dd-install-packages')
    scripts['bare'] = ['pytest -vv --benchmark-skip {args:tests}']
    if transport == 'json-adapter':
        for name in ('_dd-test', '_dd-test-cov', '_dd-benchmark'):
            scripts[name] = [command.replace('pytest ', 'python transport_entry.py ', 1) for command in scripts[name]]
    scripts['custom'] = ['python forward.py {args:tests}']
    scripts['startup'] = [
        scripts['_dd-test'][0].replace(
            '{args:tests}', '--probe-token=script-default -k script_never_matches {args:tests}'
        )
    ]
    target_python = os.environ.get('TRANSPORT_PYTHON', '3.13')
    target_pytest = os.environ.get('TRANSPORT_PYTEST', '9.0.3')
    config = {
        'envs': {
            'default': {
                'python': os.environ.get('TRANSPORT_PYTHON_EXECUTABLE', target_python),
                'skip-install': True,
                'installer': 'uv',
                'env-include': ['*'],
                'dependencies': [
                    f'pytest=={target_pytest}',
                    'pytest-cov==5.0.0',
                    'pytest-benchmark==4.0.0',
                    'requests',
                    'pyyaml',
                    'tenacity',
                ],
                'scripts': scripts,
            }
        }
    }
    (root / 'hatch.toml').write_text(tomli_w.dumps(config), encoding='utf-8')
    (root / 'pyproject.toml').write_text('[project]\nname = "transport-probe"\nversion = "0"\n', encoding='utf-8')
    env = os.environ.copy()
    for key in list(env):
        if key.startswith(('DDEV_E2E', 'HATCH_', 'PYTEST_', 'COV_CORE_', 'COVERAGE_')) or key in (
            'VIRTUAL_ENV',
            'UV_PYTHON',
            'UV_PROJECT_ENVIRONMENT',
        ):
            env.pop(key)
    repo = Path(__file__).resolve().parents[5]
    env.update(
        {
            'PYTHONPATH': os.pathsep.join([str(root), str(repo / 'datadog_checks_dev')]),
            'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1',
            'PYTEST_PLUGINS': ','.join(
                [
                    'transport_receiver',
                    'datadog_checks.dev.plugin.pytest',
                    'pytest_cov.plugin',
                    'pytest_benchmark.plugin',
                ]
            ),
            'DDEV_TRANSPORT_SENTINEL': 'EXPANDED',
            'TRANSPORT_RESULT': str(root / 'result.json'),
            'HATCH_DATA_DIR': str(root / '.hatch-data'),
            'HATCH_CACHE_DIR': str(root / '.hatch-cache'),
            'HATCH_ENV_TYPE_VIRTUAL_PATH': str(root / '.venv'),
            'HATCH_ENV_TYPE_VIRTUAL_UV_PATH': 'uv',
        }
    )
    if target_executable := os.environ.get('TRANSPORT_PYTHON_EXECUTABLE'):
        env['HATCH_PYTHON'] = target_executable
    env.pop('PYTHONUTF8', None)
    env['PYTHONIOENCODING'] = 'utf-8'
    if 'TRANSPORT_UTF8' in os.environ:
        env['PYTHONUTF8'] = os.environ['TRANSPORT_UTF8']
    hatch_python = os.environ.get('TRANSPORT_HATCH_PYTHON', sys.executable)
    hatch_version = subprocess.check_output(
        [hatch_python, '-c', 'from importlib.metadata import version; print(version("hatch"))'], text=True
    ).strip()

    def run(
        script: str,
        tokens: list[str] | None,
        *,
        expected_status: int = 0,
        validate: bool = True,
        expected_message: str | None = None,
    ) -> dict:
        result_path = root / 'result.json'
        result_path.unlink(missing_ok=True)
        context = (
            (
                json_argument_file(root, tokens, env)
                if transport == 'json-adapter'
                else argument_file(root, tokens, validate=validate)
            )
            if tokens is not None
            else no_argument_file()
        )
        with context as forwarded:
            command = [
                hatch_python,
                '-m',
                'hatch',
                '--no-color',
                '--no-interactive',
                'env',
                'run',
                '--env',
                'default',
                '--',
                script,
            ]
            if forwarded is not None:
                command.append(forwarded)
            result = subprocess.run(
                command,
                cwd=root,
                env=env,
                text=True,
                encoding='utf-8',
                errors='replace',
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=240,
            )
            # Diagnostics must not require changing the target's locale or UTF-8 mode.
            print(f'COMMAND {command!a}')
            print(result.stdout.encode('ascii', errors='backslashreplace').decode('ascii'))
            assert result.returncode == expected_status, result.stdout
        assert not list(root.glob('ddev-args-*'))
        assert 'DDEV_PYTEST_ARGV_FILE' not in env
        if expected_message is not None:
            assert expected_message in result.stdout
            return {}
        data = json.loads(result_path.read_text(encoding='utf-8'))
        assert data['status'] == expected_status
        assert data['python'].startswith(target_python + '.')
        assert data['pytest'] == target_pytest
        assert Path(data['executable']).parent.parent == root / '.venv'
        assert 'datadog_checks.dev.plugin.pytest' in data['plugins']
        print('PYTEST_BOUNDARY ' + json.dumps(data, ensure_ascii=True))
        return data

    baseline = run('test', None)
    assert baseline['paths'] == ['tests']
    assert len(baseline['selected']) == 5
    print(
        f'ORDINARY_HATCH_BASELINE hatch={hatch_version} python={baseline["python"]} pytest={baseline["pytest"]} passed'
    )

    tokens = [
        '',
        'two words',
        ' leading and trailing ',
        '"double" and \'single\'',
        'back\\slash\\',
        'café 雪 🐍',
        'C:\\Program Files\\Datadog\\tests\\',
        r'\\server\share\test.py::test_case[a b]',
        'tests/test_unit.py::test_node[node with spaces 雪]',
        '{env:DDEV_TRANSPORT_SENTINEL}',
        '{args:EXPANDED}',
        '{matrix:version}',
        '$DDEV_TRANSPORT_SENTINEL',
        '${DDEV_TRANSPORT_SENTINEL}',
        '%DDEV_TRANSPORT_SENTINEL%',
        '!DDEV_TRANSPORT_SENTINEL!',
        '^&|<>()',
        '$(touch posix-sentinel)',
        '`touch backtick-sentinel`',
        '; touch separator-sentinel',
        '& echo executed > windows-sentinel',
        '&& echo executed > and-sentinel',
        '| echo executed > pipe-sentinel',
        '%COMSPEC% /c echo executed > comspec-sentinel',
    ]
    payload = [*(token for value in tokens for token in ('--probe-token', value)), 'tests']
    if os.environ.get('TRANSPORT_EXPECT') == 'decode-error':
        with pytest.raises(AssertionError, match='UnicodeDecodeError'):
            run('test', payload)
        assert not list(root.glob('ddev-args-*'))
        print(
            f'TRANSPORT_RESULT expected=decode-error platform={sys.platform} hatch={hatch_version} '
            f'python={target_python} pytest={target_pytest}'
        )
        return
    if os.environ.get('TRANSPORT_EXPECT') == 'unsupported':
        data = run('test', payload, expected_status=4)
        assert data['tokens'] == []
        assert data['paths'][0].startswith('@ddev-args-')
        print(
            f'TRANSPORT_RESULT expected=unsupported platform={sys.platform} hatch={hatch_version} '
            f'python={data["python"]} pytest={data["pytest"]}'
        )
        return
    data = run('test', payload)
    assert data['tokens'] == tokens
    for name in ('posix', 'backtick', 'separator', 'windows', 'and', 'pipe', 'comspec'):
        assert not (root / f'{name}-sentinel').exists()

    separators = '\v\f\x1c\x1d\x1e\x85\u2028\u2029'
    values = [f'left{separator}right' for separator in separators]
    data = run(
        'test',
        [*(f'--probe-token={value}' for value in values), 'tests'],
        expected_status=0 if transport == 'json-adapter' else 4,
        validate=False,
    )
    assert data['tokens'] == (values if transport == 'json-adapter' else ['left'] * len(separators))
    print(
        'UNICODE_SEPARATOR_RESULT '
        + json.dumps(
            {
                'transport': transport,
                'codepoints': [f'U+{ord(char):04X}' for char in separators],
                'preserved': transport == 'json-adapter',
            }
        )
    )
    if transport == 'json-adapter':
        run('bare', payload, expected_status=4, expected_message='unrecognized arguments: --ddev-pytest-argv=')
        (root / 'startup_plugin.py').write_text(
            'def pytest_addoption(parser):\n    parser.addoption("--startup-value")\n', encoding='utf-8'
        )
        alternate = root / 'alternate'
        alternate.mkdir()
        (root / 'alternate.ini').write_text(
            '[pytest]\naddopts = --probe-token=config-default -k config_never_matches\n', encoding='utf-8'
        )
        env['PYTEST_ADDOPTS'] = '--probe-token=environment-default -k environment_never_matches'
        data = run(
            'startup',
            [
                '-p',
                'startup_plugin',
                '-c',
                'alternate.ini',
                '--rootdir',
                str(alternate),
                '--startup-value=loaded',
                '--probe-token=user-value',
                '-k',
                'node',
                'tests/test_unit.py',
            ],
        )
        assert data['tokens'] == ['config-default', 'environment-default', 'script-default', 'user-value']
        assert data['keyword'] == 'node'
        assert len(data['selected']) == 1
        assert data['rootdir'] == str(alternate)
        assert data['config'] == str(root / 'alternate.ini')
        assert 'startup_plugin' in data['plugins']
        env.pop('PYTEST_ADDOPTS')

    node = 'tests/test_unit.py::test_node[node with spaces 雪]'
    data = run('custom', [node])
    assert data['selected'] == [node]
    assert (root / 'before').read_text() == (root / 'after').read_text() == 'ran'
    if transport == 'json-adapter':
        assert json.loads((root / 'unrelated.json').read_text(encoding='utf-8'))['tokens'] == ['unrelated']
    data = run('test', ['--probe-token=next-invocation', 'tests'])
    assert data['tokens'] == ['next-invocation']
    data = run('test-cov', ['tests/test_unit.py'])
    assert len(data['selected']) == 2
    assert (root / '.coverage').is_file()
    data = run('benchmark', ['tests/test_benchmark.py', '--benchmark-min-rounds=1', '--benchmark-max-time=0.01'])
    assert data['selected'] == ['tests/test_benchmark.py::test_bench']

    env['DDEV_E2E_PARENT_PYTHON'] = sys.executable
    data = run('test', ['tests', '-m', '(not flaky) and e2e', '-k', 'plain'])
    assert data['selected'] == ['tests/test_e2e.py::test_plain']
    data = run('test', ['tests', '-m', 'unit or flaky and e2e'])
    assert len(data['selected']) == 3
    data = run('test', ['tests', '-m', '(unit or flaky) and e2e'])
    assert data['selected'] == ['tests/test_e2e.py::test_flaky']
    data = run('test', ['tests', '-m', 'unit', '-m', 'e2e'])
    assert len(data['selected']) == 2
    data = run('test', ['tests/missing.py'], expected_status=4)
    print(
        'TRANSPORT_RESULT '
        + json.dumps(
            {
                'transport': transport,
                'platform': sys.platform,
                'hatch': hatch_version,
                'python': data['python'],
                'encoding': data['encoding'],
                'utf8_mode': data['utf8_mode'],
                'pytest': target_pytest,
                'utf8_requested': os.environ.get('TRANSPORT_UTF8') == '1',
                'literal_values': len(tokens),
                'sentinels_created': 0,
                'scenarios': [
                    'literal',
                    'custom-node',
                    'default-paths',
                    'coverage',
                    'benchmark',
                    'e2e-keyword',
                    'marker-precedence',
                    'failure-cleanup',
                ],
            }
        )
    )


@contextmanager
def json_argument_file(root: Path, tokens: list[str], env: dict[str, str]) -> Iterator[str]:
    if any(character in token for token in tokens for character in '\x00\r\n'):
        raise ValueError('Pytest argv cannot contain NUL, CR or LF')
    nonce = uuid.uuid4().hex
    with tempfile.NamedTemporaryFile(
        mode='w', encoding='utf-8', prefix='ddev-args-', suffix='.json', dir=root, delete=False
    ) as stream:
        path = Path(stream.name)
        json.dump({'id': nonce, 'argv': tokens}, stream)
    env['DDEV_PYTEST_ARGV_FILE'] = str(path)
    try:
        yield '--ddev-pytest-argv=' + nonce
    finally:
        env.pop('DDEV_PYTEST_ARGV_FILE')
        path.unlink()


@contextmanager
def no_argument_file() -> Iterator[None]:
    yield None
