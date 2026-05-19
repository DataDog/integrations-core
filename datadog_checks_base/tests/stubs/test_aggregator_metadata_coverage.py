# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import pytest

from datadog_checks.base import AgentCheck


def test_calculate_metric_metadata_coverage(aggregator):
    check = AgentCheck()
    check.gauge('test.covered', 1)
    check.gauge('test.missing_metadata', 1)
    check.count('test.type_mismatch', 1)
    check.gauge('test.excluded', 1)

    coverage = aggregator.calculate_metric_metadata_coverage(
        {
            'test.covered': {'metric_type': 'gauge'},
            'test.type_mismatch': {'metric_type': 'gauge'},
            'test.missing_submission': {'metric_type': 'gauge'},
            'test.excluded': {'metric_type': 'gauge'},
        },
        check_submission_type=True,
        exclude=['test.excluded'],
    )

    assert coverage['submitted_metrics'] == {'test.covered', 'test.missing_metadata', 'test.type_mismatch'}
    assert coverage['metadata_metrics'] == {
        'test.covered',
        'test.type_mismatch',
        'test.missing_submission',
        'test.excluded',
    }
    assert coverage['covered_metrics'] == {'test.covered', 'test.type_mismatch'}
    assert coverage['missing_from_metadata'] == {'test.missing_metadata'}
    assert coverage['missing_from_submissions'] == {'test.missing_submission', 'test.excluded'}
    assert coverage['excluded_metrics'] == {'test.excluded'}
    assert coverage['submitted_count'] == 3
    assert coverage['metadata_count'] == 4
    assert coverage['covered_count'] == 2
    assert coverage['missing_from_metadata_count'] == 1
    assert coverage['missing_from_submissions_count'] == 2
    assert coverage['excluded_count'] == 1
    assert coverage['coverage_percent'] == 50
    assert coverage['type_mismatches'] == [
        {'metric_name': 'test.type_mismatch', 'expected_type': 'gauge', 'actual_type': 'count'}
    ]
    assert coverage['errors'] == {
        'Expect `test.missing_metadata` to be in metadata.csv.',
        'Expect `test.type_mismatch` to have type `gauge` but got `count`.',
    }


def test_metric_metadata_coverage_reporting_to_file(aggregator, monkeypatch, tmpdir):
    check = AgentCheck()
    check.gauge('test.covered', 1)
    coverage_file = tmpdir.join('coverage.jsonl')

    monkeypatch.setenv('DD_INTEGRATION_METRIC_COVERAGE', '1')
    monkeypatch.setenv('DD_INTEGRATION_METRIC_COVERAGE_FILE', str(coverage_file))
    monkeypatch.setenv('INPUT_TARGET', 'test_integration')
    monkeypatch.setenv('PYTEST_CURRENT_TEST', 'tests/test_example.py::test_metadata (call)')

    aggregator.assert_metrics_using_metadata(
        {
            'test.covered': {'metric_type': 'gauge'},
            'test.missing': {'metric_type': 'gauge'},
        },
        check_symmetric_inclusion=False,
    )

    [line] = coverage_file.readlines()
    payload = json.loads(line)
    assert payload['event'] == 'integration_metric_metadata_coverage'
    assert payload['integration'] == 'test_integration'
    assert payload['check_name'] == 'test_integration'
    assert payload['pytest_nodeid'] == 'tests/test_example.py::test_metadata'
    assert payload['submitted_count'] == 1
    assert payload['metadata_count'] == 2
    assert payload['covered_count'] == 1
    assert payload['coverage_percent'] == 50
    assert payload['missing_metric_names'] == ['test.missing']
    assert payload['emitted_not_in_metadata'] == []
    assert payload['excluded_metrics'] == []


def test_metric_metadata_coverage_reporting_to_stdout(aggregator, monkeypatch, capsys):
    check = AgentCheck()
    check.gauge('test.covered', 1)

    monkeypatch.setenv('DD_INTEGRATION_METRIC_COVERAGE', '1')
    monkeypatch.delenv('DD_INTEGRATION_METRIC_COVERAGE_FILE', raising=False)

    aggregator.assert_metrics_using_metadata({'test.covered': {'metric_type': 'gauge'}})

    stdout = capsys.readouterr().out.strip()
    assert stdout.startswith('DD_INTEGRATION_METRIC_COVERAGE ')
    payload = json.loads(stdout.split(' ', 1)[1])
    assert payload['submitted_count'] == 1
    assert payload['coverage_percent'] == 100


def test_metric_metadata_coverage_reporting_preserves_assertion_behavior(aggregator, monkeypatch, tmpdir):
    check = AgentCheck()
    check.gauge('test.extra', 1)
    coverage_file = tmpdir.join('coverage.jsonl')

    monkeypatch.setenv('DD_INTEGRATION_METRIC_COVERAGE', '1')
    monkeypatch.setenv('DD_INTEGRATION_METRIC_COVERAGE_FILE', str(coverage_file))

    with pytest.raises(AssertionError, match='Expect `test.extra` to be in metadata.csv'):
        aggregator.assert_metrics_using_metadata({'test.covered': {'metric_type': 'gauge'}})

    [line] = coverage_file.readlines()
    payload = json.loads(line)
    assert payload['emitted_not_in_metadata'] == ['test.extra']


def test_metric_metadata_coverage_reporting_uses_ci_results_dir(aggregator, monkeypatch, tmpdir, capsys):
    check = AgentCheck()
    check.gauge('test.covered', 1)
    results_dir = tmpdir.mkdir('results')

    monkeypatch.delenv('DD_INTEGRATION_METRIC_COVERAGE', raising=False)
    monkeypatch.delenv('DD_INTEGRATION_METRIC_COVERAGE_FILE', raising=False)
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    monkeypatch.setenv('TEST_RESULTS_DIR', str(results_dir))

    aggregator.assert_metrics_using_metadata({'test.covered': {'metric_type': 'gauge'}})

    coverage_file = results_dir.join('metric-metadata-coverage.jsonl')
    [line] = coverage_file.readlines()
    payload = json.loads(line)
    assert payload['submitted_count'] == 1
    assert payload['coverage_percent'] == 100
    assert capsys.readouterr().out.startswith('DD_INTEGRATION_METRIC_COVERAGE ')
