"""Prevent false compatibility passes and detect candidate-only failures."""

import importlib.util
import json
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    'jemalloc_smoke', Path(__file__).resolve().parents[1] / 'jemalloc_smoke.py'
)
smoke = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(smoke)


@pytest.mark.parametrize(
    ('control', 'candidate', 'expected'),
    [
        (
            {'status': 'passed', 'tests': {'a': 'passed'}},
            {'status': 'failed', 'tests': {'a': 'failed'}},
            'candidate_regression',
        ),
        (
            {'status': 'failed', 'tests': {'a': 'failed', 'b': 'passed'}},
            {'status': 'failed', 'tests': {'a': 'failed', 'b': 'failed'}},
            'candidate_regression',
        ),
        (
            {'status': 'failed', 'tests': {'a': 'failed'}},
            {'status': 'failed', 'tests': {'a': 'failed'}},
            'baseline_failure',
        ),
        (
            {'status': 'failed', 'tests': {'a': 'failed'}, 'process_ok': True},
            {'status': 'failed', 'tests': {}, 'process_ok': False},
            'candidate_regression',
        ),
        (
            {'status': 'failed', 'tests': {'a': 'failed'}},
            {'status': 'blocked', 'tests': {}},
            'coverage_gap',
        ),
        (
            {'status': 'failed', 'tests': {'a': 'failed', 'b': 'passed'}},
            {'status': 'failed', 'tests': {'a': 'failed'}},
            'coverage_difference',
        ),
        (
            {'status': 'passed', 'tests': {'a': 'passed'}},
            {'status': 'passed', 'tests': {'b': 'passed'}},
            'coverage_difference',
        ),
        ({'status': 'untested', 'tests': {}}, {'status': 'untested', 'tests': {}}, 'coverage_gap'),
        (
            {'status': 'partial', 'tests': {'a': 'passed', 'b': 'skipped'}},
            {'status': 'partial', 'tests': {'a': 'passed', 'b': 'skipped'}},
            'partial',
        ),
        ({'status': 'passed', 'tests': {'a': 'passed'}}, {}, 'missing_result'),
        ({'status': 'passed', 'tests': {'a': 'passed'}}, {'status': 'passed', 'tests': {'a': 'passed'}}, 'passed'),
    ],
)
def test_classify(control: dict, candidate: dict, expected: str):
    assert smoke.classify(control, candidate) == expected


def test_junit_preserves_collection_errors_and_skips(tmp_path: Path):
    report = tmp_path / 'junit.xml'
    report.write_text(
        '<testsuites><testsuite><testcase name="ok"/><testcase name="setup"><error/></testcase>'
        '<testcase name="optional"><skipped/></testcase></testsuite></testsuites>'
    )
    assert smoke.read_junit(report) == {'/ok': 'passed', '/setup': 'failed', '/optional': 'skipped'}


@pytest.mark.parametrize('free_provider', ['libjemalloc.so.2', 'libc.so.6'])
def test_allocator_verification_checks_free_provider(tmp_path: Path, free_provider: str):
    log = tmp_path / 'bindings.log'
    lines = []
    for caller in ('libpython3.13.so', 'libdatadog-agent-three.so'):
        lines.extend(
            [
                f"binding file /opt/{caller} [0] to /opt/libjemalloc.so.2 [0]: normal symbol `malloc'\n",
                f"binding file /opt/{caller} [0] to /opt/{free_provider} [0]: normal symbol `free'\n",
            ]
        )
    log.write_text(''.join(lines))
    assert smoke.verify_bindings(log, 'jemalloc') == (free_provider == 'libjemalloc.so.2')


def test_comparison_reports_missing_environments(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('EXPECTED_MATRIX', json.dumps({'integration': ['tls', 'postgres']}))
    monkeypatch.setenv('AGENT_IMAGE', 'agent@sha256:fixed')
    passed = {'status': 'passed', 'tests': {'tls/ok': 'passed'}}
    report = {
        'integration': 'tls',
        'image': 'agent@sha256:fixed',
        'selected_environments': ['one', 'two'],
        'environments': {'one': {'glibc': passed, 'jemalloc': passed}},
    }
    (tmp_path / 'jemalloc-results.json').write_text(json.dumps(report))
    output = tmp_path / 'comparison'
    assert smoke.compare(tmp_path, output) == 1
    rows = json.loads((output / 'comparison.json').read_text())
    assert {(row['integration'], row['environment']): row['classification'] for row in rows} == {
        ('tls', 'one'): 'passed',
        ('tls', 'two'): 'missing_result',
        ('postgres', '-'): 'missing_result',
    }
