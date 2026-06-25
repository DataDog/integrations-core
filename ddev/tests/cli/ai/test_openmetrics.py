# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import pytest

from ddev.cli.ai.openmetrics import _flow_phase_ids, _incomplete_phases, _normalize


def invoke(ddev, display_name, docker_dir, prd_file, *extra):
    """Run the command with all required options filled in, plus any extras."""
    return ddev(
        'meta',
        'ai',
        'openmetrics',
        display_name,
        '--endpoint',
        'http://localhost:9090/metrics',
        '--docker-path',
        str(docker_dir),
        '--prd',
        str(prd_file),
        *extra,
    )


@pytest.fixture
def mock_orchestrator(mocker):
    """Replace the heavy run machinery with a mock that succeeds and produces no phases gap."""
    mocker.patch('anthropic.AsyncAnthropic')
    mocker.patch('ddev.ai.tools.fs.file_access_policy.FileAccessPolicy')
    orchestrator_cls = mocker.patch('ddev.ai.runtime.orchestrator.PhaseOrchestrator')
    orchestrator_cls.return_value._failed_phase = None
    mocker.patch('ddev.cli.ai.openmetrics._incomplete_phases', return_value=[])
    return orchestrator_cls


# --- registration & help ----------------------------------------------------


def test_registered_under_meta_ai(ddev):
    result = ddev('meta', 'ai', '--help')

    assert result.exit_code == 0, result.output
    assert 'openmetrics' in result.output


def test_help_lists_options(ddev):
    result = ddev('meta', 'ai', 'openmetrics', '--help')

    assert result.exit_code == 0, result.output
    assert 'DISPLAY_NAME' in result.output
    for option in ('--endpoint', '--docker-path', '--prd', '--force', '--resume', '--timeout'):
        assert option in result.output


# --- argument parsing (click) ------------------------------------------------


def test_missing_display_name(ddev):
    result = ddev('meta', 'ai', 'openmetrics')

    assert result.exit_code == 2


@pytest.mark.parametrize('option', ['--endpoint', '--docker-path', '--prd'])
def test_required_options(ddev, docker_dir, prd_file, option):
    args = {
        '--endpoint': 'http://localhost:9090/metrics',
        '--docker-path': str(docker_dir),
        '--prd': str(prd_file),
    }
    del args[option]
    flat = [item for pair in args.items() for item in pair]

    result = ddev('meta', 'ai', 'openmetrics', 'KrakenD', *flat)

    assert result.exit_code == 2
    assert option in result.output


# --- validation aborts -------------------------------------------------------


@pytest.mark.parametrize('value', ['0', '-5'])
def test_timeout_must_be_positive(ddev, docker_dir, prd_file, value):
    result = invoke(ddev, 'KrakenD', docker_dir, prd_file, '--timeout', value)

    assert result.exit_code == 1
    assert '`--timeout` must be greater than 0.' in result.output


def test_missing_api_key(ddev, docker_dir, prd_file):
    result = invoke(ddev, 'KrakenD', docker_dir, prd_file)

    assert result.exit_code == 1
    assert 'No Anthropic API key found' in result.output


def test_docker_path_not_a_directory(ddev, prd_file, with_api_key):
    result = ddev(
        'meta',
        'ai',
        'openmetrics',
        'KrakenD',
        '--endpoint',
        'http://localhost:9090/metrics',
        '--docker-path',
        str(prd_file),  # a file, not a directory
        '--prd',
        str(prd_file),
    )

    assert result.exit_code == 1
    assert 'is not a directory' in result.output


def test_prd_file_missing(ddev, docker_dir, tmp_path, with_api_key):
    missing = tmp_path / 'nope.md'

    result = invoke(ddev, 'KrakenD', docker_dir, missing)

    assert result.exit_code == 1
    assert 'does not exist' in result.output


def test_prd_file_empty(ddev, docker_dir, tmp_path, with_api_key):
    empty = tmp_path / 'empty.md'
    empty.write_text('   \n')

    result = invoke(ddev, 'KrakenD', docker_dir, empty)

    assert result.exit_code == 1
    assert 'is empty' in result.output


def test_display_name_not_normalizable(ddev, docker_dir, prd_file, with_api_key):
    result = invoke(ddev, '@@@', docker_dir, prd_file)

    assert result.exit_code == 1
    assert 'Could not derive an integration name' in result.output


def test_resume_and_force_mutually_exclusive(ddev, docker_dir, prd_file, with_api_key):
    result = invoke(ddev, 'KrakenD', docker_dir, prd_file, '--resume', '--force')

    assert result.exit_code == 1
    assert 'mutually exclusive' in result.output


def test_resume_without_previous_run(ddev, docker_dir, prd_file, with_api_key, ai_repo):
    result = invoke(ddev, 'KrakenD', docker_dir, prd_file, '--resume')

    assert result.exit_code == 1
    assert 'No previous run found' in result.output


def test_existing_integration_without_force(ddev, docker_dir, prd_file, with_api_key, ai_repo):
    (ai_repo / 'krakend').mkdir()

    result = invoke(ddev, 'KrakenD', docker_dir, prd_file)

    assert result.exit_code == 1
    assert 'already exists' in result.output


# --- orchestrator path (mocked) ----------------------------------------------


def test_force_removes_existing_integration(ddev, docker_dir, prd_file, with_api_key, ai_repo, mock_orchestrator):
    integration_dir = ai_repo / 'krakend'
    integration_dir.mkdir()
    (integration_dir / 'leftover.txt').write_text('stale')

    result = invoke(ddev, 'KrakenD', docker_dir, prd_file, '--force')

    assert result.exit_code == 0, result.output
    assert 'Removed existing' in result.output
    assert not integration_dir.exists()


def test_successful_run_wires_runtime_variables(ddev, docker_dir, prd_file, with_api_key, ai_repo, mock_orchestrator):
    result = invoke(ddev, 'KrakenD', docker_dir, prd_file)

    assert result.exit_code == 0, result.output
    assert "Integration 'krakend' generated." in result.output
    assert 'Generated artifacts' in result.output

    mock_orchestrator.return_value.run.assert_called_once()
    kwargs = mock_orchestrator.call_args.kwargs
    assert kwargs['resume'] is False
    assert kwargs['max_timeout'] == pytest.approx(3600.0)
    assert kwargs['runtime_variables'] == {
        'endpoint_url': 'http://localhost:9090/metrics',
        'integration': 'KrakenD',
        'docker_source_path': str(docker_dir.resolve()),
        'prd': 'Drop the foo_total metric.',
    }


def test_custom_timeout_passed_through(ddev, docker_dir, prd_file, with_api_key, ai_repo, mock_orchestrator):
    result = invoke(ddev, 'KrakenD', docker_dir, prd_file, '--timeout', '120')

    assert result.exit_code == 0, result.output
    assert mock_orchestrator.call_args.kwargs['max_timeout'] == pytest.approx(120.0)


def test_run_failure_aborts(ddev, docker_dir, prd_file, with_api_key, ai_repo, mock_orchestrator):
    mock_orchestrator.return_value.run.side_effect = RuntimeError('boom')
    mock_orchestrator.return_value._failed_phase = 'inspect_endpoint'

    result = invoke(ddev, 'KrakenD', docker_dir, prd_file)

    assert result.exit_code == 1
    assert 'Pipeline failed: RuntimeError: boom' in result.output
    assert 'failed phase: inspect_endpoint' in result.output
    assert 'Re-run with `--resume`' in result.output


def test_incomplete_phases_aborts(ddev, docker_dir, prd_file, with_api_key, ai_repo, mocker, mock_orchestrator):
    mocker.patch('ddev.cli.ai.openmetrics._incomplete_phases', return_value=['write_tests', 'write_readme'])

    result = invoke(ddev, 'KrakenD', docker_dir, prd_file)

    assert result.exit_code == 1
    assert "did not reach 'success': write_tests, write_readme" in result.output
    assert 'Generated artifacts' in result.output


def test_resume_run_skips_when_checkpoint_exists(ddev, docker_dir, prd_file, with_api_key, ai_repo, mock_orchestrator):
    checkpoint = ai_repo / '.ddev' / 'ai-runs' / 'krakend' / 'checkpoints.yaml'
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text('inspect_endpoint:\n  status: success\n')

    result = invoke(ddev, 'KrakenD', docker_dir, prd_file, '--resume')

    assert result.exit_code == 0, result.output
    assert 'Resuming the previous run' in result.output
    assert mock_orchestrator.call_args.kwargs['resume'] is True


# --- helpers -----------------------------------------------------------------


@pytest.mark.parametrize(
    'display_name, expected',
    [
        ('KrakenD', 'krakend'),
        ('My Cool App', 'my_cool_app'),
        ('foo-bar.baz', 'foo_bar_baz'),
        ('  Spaced  ', 'spaced'),
        ('Multi___Score', 'multi_score'),
        ('123 Numbers', '123_numbers'),
        ('!!!', ''),
    ],
)
def test_normalize(display_name, expected):
    assert _normalize(display_name) == expected


def test_flow_phase_ids_preserves_order(tmp_path):
    flow_yaml = tmp_path / 'flow.yaml'
    flow_yaml.write_text(
        'flow:\n  - phase: inspect_endpoint\n  - phase: rename_metrics\n  - phase: build_integration\n'
    )

    assert _flow_phase_ids(flow_yaml) == ['inspect_endpoint', 'rename_metrics', 'build_integration']


def test_incomplete_phases_returns_all_when_no_checkpoint(tmp_path):
    flow_yaml = tmp_path / 'flow.yaml'
    flow_yaml.write_text('flow:\n  - phase: a\n  - phase: b\n')

    assert _incomplete_phases(tmp_path / 'absent.yaml', flow_yaml) == ['a', 'b']


def test_incomplete_phases_filters_successful(tmp_path, mocker):
    flow_yaml = tmp_path / 'flow.yaml'
    flow_yaml.write_text('flow:\n  - phase: a\n  - phase: b\n  - phase: c\n')
    checkpoint = tmp_path / 'checkpoints.yaml'
    checkpoint.write_text('placeholder: {}\n')
    mocker.patch(
        'ddev.ai.runtime.checkpoints.CheckpointManager.successful_phases',
        return_value={'a', 'c'},
    )

    assert _incomplete_phases(checkpoint, flow_yaml) == ['b']
