"""Branch-only paired Agent E2E runs and coverage comparison."""

from __future__ import annotations

import argparse
import csv
import fnmatch
import json
import os
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
MODES = ('glibc', 'jemalloc')


def _write(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def _command(args: list[str], log: Path, *, cwd: Path = ROOT, timeout: int = 1800) -> int:
    """Bound subprocess trees so a hung fixture cannot prevent the other allocator run."""
    log.parent.mkdir(parents=True, exist_ok=True)
    print(f'Running {args[0]} {args[1:3]} (log: {log})', flush=True)
    with log.open('w') as output:
        process = subprocess.Popen(args, cwd=cwd, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            return 124


def _ddev(*args: str) -> list[str]:
    return [sys.executable, '-m', 'ddev', '--no-interactive', *args]


def plan(targets: str) -> dict[str, list[str]]:
    available = []
    for manifest in sorted(ROOT.glob('*/manifest.json')):
        directory = manifest.parent
        data = json.loads(manifest.read_text())
        if (
            'Supported OS::Linux' in data.get('tile', {}).get('classifier_tags', [])
            and (directory / 'pyproject.toml').exists()
            and (directory / 'datadog_checks').is_dir()
        ):
            available.append(directory.name)
    selected = available if targets == 'all' else sorted(set(re.split(r'[\s,]+', targets.strip())))
    if not selected or set(selected) - set(available):
        raise ValueError(f'Unknown or unsupported Linux targets: {set(selected) - set(available)}')
    if len(selected) > 256:
        raise ValueError('Split the campaign into batches of at most 256 integrations.')
    return {'integration': selected}


def read_junit(path: Path) -> dict[str, str]:
    """Compare executed test identities, including skips, rather than just exit codes."""
    if not path.exists():
        return {}
    tests = {}
    for case in ET.parse(path).getroot().iter('testcase'):
        key = f'{case.get("classname", "")}/{case.get("name", "")}'
        tests[key] = (
            'skipped'
            if case.find('skipped') is not None
            else 'failed'
            if case.find('failure') is not None or case.find('error') is not None
            else 'passed'
        )
    return tests


def verify_bindings(path: Path, mode: str) -> bool:
    text = path.read_text()
    rows = re.findall(r'binding file ([^\n]+?) to ([^\n]+?): normal symbol `(malloc|calloc|realloc|free)', text)
    expected = 'libc.so.6' if mode == 'glibc' else 'libjemalloc'
    for caller in ('libpython3.', 'libdatadog-agent-three'):
        reached = [row for row in rows if caller in row[0]]
        if not {'malloc', 'free'} <= {row[2] for row in reached}:
            return False
        if any(expected not in row[1] for row in reached):
            return False
    return True


def _metadata(integration: str, environment: str) -> dict[str, Any]:
    from platformdirs import user_data_dir

    data_dir = Path(os.getenv('DDEV_DATA_DIR') or user_data_dir('ddev', appauthor=False))
    path = data_dir / 'env' / integration / environment / 'metadata.json'
    return json.loads(path.read_text()) if path.exists() else {}


def run_case(
    integration: str, environment: str, mode: str, args: argparse.Namespace, directory: Path
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {'status': 'incomplete', 'tests': {}}
    start = time.monotonic()
    try:
        preload = args.base_preload + ([args.library] if mode == 'jemalloc' else [])
        command = _ddev(
            'env',
            'start',
            integration,
            environment,
            '--agent',
            args.image,
            '-e',
            f'LD_PRELOAD={":".join(preload)}',
            '-e',
            f'MALLOC_CONF={args.malloc_conf if mode == "jemalloc" else ""}',
        )
        result['setup_exit'] = _command(command, directory / 'setup.log')
        if result['setup_exit']:
            result['status'] = 'blocked'
            return result
        metadata = _metadata(integration, environment)
        result['fixture_package_mutations'] = metadata.get('post_install_commands', [])
        if metadata.get('agent_type', 'docker') != 'docker':
            result['status'] = 'unsupported_agent_backend'
            return result
        container = f'dd_{integration}_{environment}'
        # An explicit diagnostic invocation reaches the real embedded Python/rtloader.
        # Its check result may legitimately fail for discovery/error-path fixtures.
        result['diagnostic_exit'] = _command(
            [
                'docker',
                'exec',
                container,
                'env',
                '-u',
                'LD_DEBUG_OUTPUT',
                'LD_DEBUG=bindings',
                'agent',
                'check',
                integration,
                '--json',
            ],
            directory / 'bindings.log',
            timeout=120,
        )
        result['activation_verified'] = verify_bindings(directory / 'bindings.log', mode)
        result['test_exit'] = _command(
            _ddev(
                'env', 'test', integration, environment, '--', '-k', 'not fips', f'--junitxml={directory / "junit.xml"}'
            ),
            directory / 'tests.log',
        )
        result['tests'] = read_junit(directory / 'junit.xml')
        _command(['docker', 'logs', container], directory / 'agent.log', timeout=60)
        _command(
            ['docker', 'exec', container, 'agent', 'status', '--json'], directory / 'agent-status.json', timeout=60
        )
        state_exit = _command(
            ['docker', 'inspect', '--format', '{{json .State}}', container],
            directory / 'state.json',
            timeout=60,
        )
        state = json.loads((directory / 'state.json').read_text()) if state_exit == 0 else {}
        result['process_ok'] = state.get('Running', False) and not state.get('OOMKilled', False)
        executed = [status for status in result['tests'].values() if status != 'skipped']
        if result['test_exit'] == 5 or (result['test_exit'] == 0 and not executed):
            result['status'] = 'untested'
        elif result['test_exit'] != 0 or 'failed' in executed or not result['process_ok']:
            result['status'] = 'failed'
        elif not result['activation_verified']:
            result['status'] = 'activation_unverified'
        elif 'skipped' in result['tests'].values() or result['fixture_package_mutations']:
            result['status'] = 'partial'
        else:
            result['status'] = 'passed'
    except Exception as error:
        result['status'] = 'blocked'
        result['error'] = str(error)
    finally:
        result['cleanup_exit'] = _command(
            _ddev('env', 'stop', integration, 'all'),
            directory / 'cleanup.log',
            timeout=180,
        )
        if result['cleanup_exit']:
            result['status'] = 'cleanup_failed'
        result['seconds'] = round(time.monotonic() - start, 2)
        _write(directory / 'result.json', result)
    return result


def run_campaign(args: argparse.Namespace) -> None:
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        'integration': args.integration,
        'image': args.image,
        'malloc_conf': args.malloc_conf,
        'checkout_sha': os.getenv('GITHUB_SHA'),
        'environments': {},
        'scope': 'Linux Docker E2E; FIPS tests excluded; shipped integration packages.',
    }
    report_path = output / 'jemalloc-results.json'
    _write(report_path, report)
    discovery_exit = _command(
        [sys.executable, '-m', 'hatch', 'env', 'show', '--json'],
        output / 'environments.json',
        cwd=ROOT / args.integration,
    )
    if discovery_exit:
        report['error'] = 'Environment discovery failed; see environments.json'
        _write(report_path, report)
        return
    environments = json.loads((output / 'environments.json').read_text())
    names = [
        name
        for name, config in environments.items()
        if config.get('e2e-env')
        and config.get('test-env')
        and (not config.get('platforms') or 'linux' in config['platforms'])
        and fnmatch.fnmatchcase(name, args.environments)
    ]
    report['selected_environments'] = names
    _write(report_path, report)
    if not names:
        report['error'] = 'No eligible E2E environments matched.'
        _write(report_path, report)
        return
    if os.getenv('DDEV_E2E_DOCKER_NO_PULL') != '1' and _command(
        ['docker', 'pull', args.image], output / 'image-pull.log'
    ):
        report['error'] = 'Agent image pull failed.'
        _write(report_path, report)
        return
    image_config = subprocess.check_output(['docker', 'image', 'inspect', args.image], text=True)
    image = json.loads(image_config)[0]
    image_env = dict(entry.split('=', 1) for entry in image['Config'].get('Env', []) if '=' in entry)
    args.base_preload = [
        item
        for item in re.split(r'[:\s]+', image_env.get('LD_PRELOAD', ''))
        if item and 'jemalloc' not in Path(item).name
    ]
    report['image_id'] = image['Id']
    report['base_preload'] = args.base_preload
    # All envs in the pair reuse the already-pinned artifact, never a moving tag.
    os.environ['DDEV_E2E_DOCKER_NO_PULL'] = '1'
    for name in names:
        report['environments'][name] = {}
        for mode in MODES:
            directory = output / name / mode
            report['environments'][name][mode] = {'status': 'incomplete', 'tests': {}}
            _write(report_path, report)
            report['environments'][name][mode] = run_case(args.integration, name, mode, args, directory)
            _write(report_path, report)


def classify(control: dict[str, Any], candidate: dict[str, Any]) -> str:
    if not control or not candidate or 'incomplete' in (control['status'], candidate['status']):
        return 'missing_result'
    if control['status'] in ('passed', 'partial') and candidate['status'] == 'failed':
        return 'candidate_regression'
    if control['status'] == 'failed':
        if control.get('process_ok') is True and candidate.get('process_ok') is False:
            return 'candidate_regression'
        if candidate['status'] not in ('passed', 'partial', 'failed'):
            return 'coverage_gap'
        failed_before = {key for key, value in control['tests'].items() if value == 'failed'}
        failed_after = {key for key, value in candidate['tests'].items() if value == 'failed'}
        if failed_after - failed_before:
            return 'candidate_regression'
        if set(control['tests']) != set(candidate['tests']):
            return 'coverage_difference'
        return 'baseline_failure'
    if control['status'] not in ('passed', 'partial') or candidate['status'] not in ('passed', 'partial'):
        return 'coverage_gap'
    if control['tests'] != candidate['tests']:
        return 'coverage_difference'
    return 'partial' if 'partial' in (control['status'], candidate['status']) else 'passed'


def compare(results: Path, output: Path) -> int:
    expected = json.loads(os.environ['EXPECTED_MATRIX'])['integration']
    reports = {}
    for path in results.rglob('jemalloc-results.json'):
        report = json.loads(path.read_text())
        if report['integration'] in reports:
            raise ValueError(f'Duplicate integration artifact: {report["integration"]}')
        reports[report['integration']] = report
    rows = []
    for integration in expected:
        report = reports.get(integration)
        if not report or not report['environments']:
            rows.append(
                {
                    'integration': integration,
                    'environment': '-',
                    'classification': 'missing_result' if not report else 'coverage_gap',
                    'glibc': '-',
                    'jemalloc': '-',
                    'tests': 0,
                    'note': report.get('error', '') if report else 'Artifact missing',
                }
            )
            continue
        for name in report.get('selected_environments', report['environments']):
            pair = report['environments'].get(name, {})
            control, candidate = (pair.get(mode, {}) for mode in MODES)
            classification = classify(control, candidate)
            if report['image'] != os.environ['AGENT_IMAGE']:
                classification = 'artifact_mismatch'
            rows.append(
                {
                    'integration': integration,
                    'environment': name,
                    'classification': classification,
                    'glibc': control.get('status', '-'),
                    'jemalloc': candidate.get('status', '-'),
                    'tests': sum(value != 'skipped' for value in candidate.get('tests', {}).values()),
                    'note': 'Fixture changes native packages'
                    if control.get('fixture_package_mutations') or candidate.get('fixture_package_mutations')
                    else '',
                }
            )
    output.mkdir(parents=True, exist_ok=True)
    _write(output / 'comparison.json', rows)
    with (output / 'comparison.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    counts = {
        name: sum(row['classification'] == name for row in rows)
        for name in sorted({row['classification'] for row in rows})
    }
    lines = [
        'Jemalloc E2E comparison',
        '',
        f'Agent artifact: `{os.environ["AGENT_IMAGE"]}`',
        '',
        'Counts are integration/environment pairs; gaps and partial coverage are not compatibility passes.',
        '',
        ', '.join(f'{name}: {count}' for name, count in counts.items()),
        '',
        '| Integration | Environment | Result | glibc | jemalloc | Executed tests | Note |',
        '| --- | --- | --- | --- | --- | --- | --- |',
    ]
    lines.extend(
        '| '
        + ' | '.join(
            str(row[key])
            for key in ('integration', 'environment', 'classification', 'glibc', 'jemalloc', 'tests', 'note')
        )
        + ' |'
        for row in rows
    )
    text = '\n'.join(lines) + '\n'
    (output / 'comparison.md').write_text(text)
    if summary := os.getenv('GITHUB_STEP_SUMMARY'):
        with Path(summary).open('a') as stream:
            stream.write(text)
    print(', '.join(f'{name}: {count}' for name, count in counts.items()))
    return int(
        any(
            row['classification']
            in ('candidate_regression', 'missing_result', 'coverage_difference', 'artifact_mismatch')
            for row in rows
        )
    )


def main() -> int:
    parser = argparse.ArgumentParser(__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    planning = commands.add_parser('plan')
    planning.add_argument('--targets', required=True)
    running = commands.add_parser('run')
    running.add_argument('--integration', required=True)
    running.add_argument('--environments', default='*')
    running.add_argument('--image', required=True)
    running.add_argument('--library', default='/opt/datadog-agent/embedded/lib/libjemalloc.so.2')
    running.add_argument('--malloc-conf', default='')
    running.add_argument('--output', type=Path, required=True)
    comparison = commands.add_parser('compare')
    comparison.add_argument('--results', type=Path, required=True)
    comparison.add_argument('--output', type=Path, required=True)
    cleanup = commands.add_parser('cleanup')
    cleanup.add_argument('--integration', required=True)
    cleanup.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'plan':
        matrix = json.dumps(plan(args.targets))
        if output := os.getenv('GITHUB_OUTPUT'):
            with Path(output).open('a') as stream:
                stream.write(f'matrix={matrix}\n')
        print(matrix)
    elif args.command == 'run':
        run_campaign(args)
    elif args.command == 'compare':
        return compare(args.results, args.output)
    else:
        return _command(_ddev('env', 'stop', args.integration, 'all'), args.output / 'final-cleanup.log', timeout=180)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        # Surface runner failures in check annotations as well as downloadable logs.
        message = f'{type(error).__name__}: {error}'.replace('%', '%25').replace('\r', '%0D').replace('\n', '%0A')
        print(f'::error title=Jemalloc smoke runner::{message}', flush=True)
        raise
