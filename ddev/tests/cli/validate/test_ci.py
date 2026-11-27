# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

import pytest
import yaml

from ddev.cli.validate.ci import _get_test_workflow_settings

TEST_WORKFLOW_PREFIX = 'DataDog/integrations-core/.github/workflows/test-target.yml@'


def test_missing_hatch_toml(ddev, repository, helpers):
    import os

    check = 'apache'
    hatch_file = repository.path / check / 'hatch.toml'
    os.remove(hatch_file)
    result = ddev("validate", "ci")

    assert result.exit_code == 1, result.output
    error = "CI configuration is not in sync, try again with the `--sync` flag"
    assert error in helpers.remove_trailing_spaces(result.output)


def test_validate_ci_success(ddev, helpers):
    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output
    assert helpers.remove_trailing_spaces(result.output) == helpers.dedent(
        """
        CI configuration validation

        Passed: 1
        """
    )


def _remove_service(config_path):
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config['services'] = [s for s in config.get('services', []) if s.get('id') != 'apache']

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _set_wrong_paths(config_path):
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    for service in config.get('services', []):
        if service.get('id') == 'active_directory':
            service['paths'] = ['wrong/path/']
            break

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _add_stale_service(config_path):
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config.setdefault('services', []).append({'id': 'stale_service', 'paths': ['stale_service/tests/']})

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _add_duplicate_service(config_path: Path) -> None:
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    duplicate_service = next(service for service in config['services'] if service.get('id') == 'active_directory')
    config['services'].append({'id': duplicate_service['id'], 'paths': list(duplicate_service['paths'])})

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _remove_gates(config_path: Path) -> None:
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config.pop('gates', None)

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


def _clear_gates(config_path: Path) -> None:
    with config_path.open(encoding='utf-8') as f:
        config = yaml.safe_load(f)

    config['gates'] = []

    with config_path.open(mode='w', encoding='utf-8') as f:
        yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)


@pytest.mark.parametrize(
    'corrupt_config, expected_error',
    [
        pytest.param(_remove_service, "Code coverage config has 1 missing service", id='missing_services'),
        pytest.param(
            _set_wrong_paths,
            "Service `active_directory` has incorrect coverage source paths",
            id='incorrect_paths',
        ),
        pytest.param(
            _add_stale_service, "Code coverage config has 1 stale service: stale_service", id='stale_services'
        ),
        pytest.param(
            _add_duplicate_service,
            "Code coverage config has 1 duplicate service ID: active_directory",
            id='duplicate_services',
        ),
        pytest.param(_remove_gates, "Code coverage config has no coverage gates", id='missing_gates'),
        pytest.param(_clear_gates, "Code coverage config has no coverage gates", id='empty_gates'),
    ],
)
def test_code_coverage_config(ddev, repository, helpers, corrupt_config, expected_error):
    result = ddev("validate", "ci", "--sync")
    assert result.exit_code == 0, result.output

    config_path = repository.path / 'code-coverage.datadog.yml'
    corrupt_config(config_path)

    result = ddev("validate", "ci")
    assert result.exit_code == 1, f"Expected validation to detect corrupted config: {result.output}"
    assert expected_error in helpers.remove_trailing_spaces(result.output)

    result = ddev("validate", "ci", "--sync")
    assert result.exit_code == 0, f"Expected --sync to fix corrupted config: {result.output}"

    result = ddev("validate", "ci")
    assert result.exit_code == 0, f"Expected validation to pass after sync: {result.output}"


def test_code_coverage_file_missing(ddev, repository, helpers):
    (repository.path / 'code-coverage.datadog.yml').unlink()

    result = ddev("-c", "validate", "ci")
    assert result.exit_code == 1, result.output
    assert "Unable to find the code coverage config file" in helpers.remove_trailing_spaces(result.output)


def test_code_coverage_skipped_for_extras(ddev, repository, helpers, config_file):
    config_file.model.repos['extras'] = str(repository.path)
    config_file.model.repo = 'extras'
    config_file.save()

    # Remove the coverage file entirely — extras should not care
    coverage_file = repository.path / 'code-coverage.datadog.yml'
    if coverage_file.exists():
        coverage_file.unlink()

    result = ddev('validate', 'ci', '--sync')
    assert result.exit_code == 0, result.output

    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    'repo_name',
    [
        pytest.param('core', id='core'),
        pytest.param('extras', id='extras'),
        pytest.param('marketplace', id='marketplace'),
    ],
)
def test_minimum_base_package(ddev, repository, helpers, repo_name, config_file):
    config_file.model.repos[repo_name] = str(repository.path)
    config_file.model.repo = repo_name
    config_file.save()

    result = ddev('validate', 'ci', '--sync')
    assert result.exit_code == 0, result.output

    test_all = repository.path / '.github' / 'workflows' / 'test-all.yml'
    with test_all.open(encoding='utf-8') as file:
        test_all_yaml_info = yaml.safe_load(file)

    for job in test_all_yaml_info['jobs'].values():
        if repo_name == 'extras':
            assert 'minimum-base-package' not in job['with']
        else:
            assert '${{ inputs.minimum-base-package }}' == job['with']['minimum-base-package']

    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    ('repo_name', 'filename', 'content', 'expected_error'),
    [
        pytest.param(
            'core',
            'test-all.yml',
            'jobs: [}\n',
            "line 1, column 8: expected the node content, but found '}'. "
            'Fix the YAML syntax or resolve merge conflicts',
            id='core-syntax',
        ),
        pytest.param(
            'extras',
            'test-all-windows.yml',
            '<<<<<<< HEAD\njobs: {}\n=======\njobs: {}\n>>>>>>> branch\n',
            'line 2, column 5: mapping values are not allowed here. Fix the YAML syntax or resolve merge conflicts',
            id='extras-windows-conflict',
        ),
        pytest.param('extras', 'test-all.yml', '[]\n', "'workflow' must be a mapping", id='workflow-list'),
        pytest.param(
            'core',
            'test-all-windows.yml',
            'jobs:\n',
            "'jobs' must be a mapping. Use 'jobs: {}' if the section is intentionally empty.",
            id='core-windows-empty-jobs',
        ),
        pytest.param(
            'extras',
            'test-all.yml',
            'jobs:\n',
            "'jobs' must be a mapping. Use 'jobs: {}' if the section is intentionally empty.",
            id='extras-empty-jobs',
        ),
        pytest.param('extras', 'test-all.yml', 'jobs: []\n', "'jobs' must be a mapping", id='jobs-list'),
        pytest.param(
            'extras',
            'test-all.yml',
            'jobs:\n  broken:\n',
            "'jobs.broken' must be a mapping",
            id='empty-job',
        ),
        pytest.param(
            'extras',
            'test-all.yml',
            'jobs:\n  broken:\n    uses: []\n',
            "'jobs.broken.uses' must be a string",
            id='uses-list',
        ),
        pytest.param(
            'extras',
            'test-all.yml',
            'jobs:\n  broken:\n    with: []\n',
            "'jobs.broken.with' must be a mapping",
            id='with-list',
        ),
        pytest.param(
            'extras',
            'test-all.yml',
            f'jobs:\n  broken:\n    uses: {TEST_WORKFLOW_PREFIX}master\n    with:\n      ddev-version: []\n',
            "'jobs.broken.with.ddev-version' must be a string",
            id='pin-list',
        ),
        pytest.param(
            'extras',
            'test-all.yml',
            'on:\n  workflow_call: []\n',
            "'on.workflow_call' must be a mapping",
            id='workflow-call-list',
        ),
        pytest.param(
            'extras',
            'test-all.yml',
            'on:\n  workflow_call:\n    inputs: []\n',
            "'on.workflow_call.inputs' must be a mapping",
            id='inputs-list',
        ),
    ],
)
def test_ci_generator_rejects_invalid_workflows(
    ddev,
    repository,
    config_file,
    repo_name: str,
    filename: str,
    content: str,
    expected_error: str,
):
    config_file.model.repos[repo_name] = str(repository.path)
    config_file.model.repo = repo_name
    config_file.save()
    paths = [repository.path / '.github/workflows' / name for name in ('test-all.yml', 'test-all-windows.yml')]
    for path in paths:
        path.write_text('name: Test CI\njobs: {}\n')
    (repository.path / '.github/workflows' / filename).write_text(content)
    original = {path: path.read_bytes() for path in paths}

    result = ddev('validate', 'ci', '--sync')

    assert result.exit_code == 1, result.output
    output = ' '.join(result.output.split())
    assert f'Error: {filename}:' in output
    assert expected_error in output
    assert {path: path.read_bytes() for path in paths} == original


@pytest.mark.parametrize(
    ('repo_name', 'event_names', 'call_event'),
    [('core', '[push, pull_request]', 'workflow_call:'), ('extras', 'workflow_call', 'workflow_call: null')],
)
def test_ci_generator_preserves_trigger_headers(
    ddev,
    repository,
    config_file,
    repo_name: str,
    event_names: str,
    call_event: str,
):
    config_file.model.repos[repo_name] = str(repository.path)
    config_file.model.repo = repo_name
    config_file.save()
    headers = {
        repository.path / '.github/workflows/test-all.yml': f'name: Test CI\non:\n  {call_event}\n',
        repository.path / '.github/workflows/test-all-windows.yml': f'name: Test CI\non: {event_names}\n',
    }
    for path, header in headers.items():
        path.write_text(f'{header}\njobs: {{}}\n')

    result = ddev('validate', 'ci', '--sync')

    assert result.exit_code == 0, result.output
    for path, header in headers.items():
        assert path.read_text().startswith(header)
    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    ('repo_name', 'content'),
    [
        pytest.param('extras', None, id='missing-file'),
        pytest.param('core', '', id='empty-file'),
        pytest.param('extras', 'name: Test CI\n', id='missing-jobs'),
        pytest.param('core', 'name: Test CI\njobs: {}\n', id='core-empty-mapping'),
        pytest.param('extras', 'name: Test CI\njobs: {}\n', id='extras-empty-mapping'),
    ],
)
def test_ci_generator_initializes_workflows(ddev, repository, config_file, repo_name: str, content: str | None):
    config_file.model.repos[repo_name] = str(repository.path)
    config_file.model.repo = repo_name
    config_file.save()
    paths = [repository.path / '.github/workflows' / name for name in ('test-all.yml', 'test-all-windows.yml')]
    for path in paths:
        if content is None:
            path.unlink()
        else:
            path.write_text(content)

    result = ddev('validate', 'ci', '--sync')

    assert result.exit_code == 0, result.output
    for path in paths:
        assert yaml.safe_load(path.read_text())['jobs']
    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize('repo_name', ['extras', 'marketplace', 'internal'])
@pytest.mark.parametrize('pin_source', ['job', 'input'])
def test_ci_generator_preserves_tooling_pins(ddev, repository, config_file, repo_name: str, pin_source: str):
    config_file.model.repos[repo_name] = str(repository.path)
    config_file.model.repo = repo_name
    config_file.save()
    expected = {}
    for filename, revision in [('test-all.yml', 'a' * 40), ('test-all-windows.yml', 'b' * 40)]:
        path = repository.path / '.github/workflows' / filename
        workflow = yaml.safe_load(path.read_text())
        workflow['on'] = workflow.pop(True)
        inputs = workflow['on']['workflow_call']['inputs']
        for job in workflow['jobs'].values():
            job['uses'] = f'{TEST_WORKFLOW_PREFIX}{revision}'
            if pin_source == 'job':
                job['with']['ddev-version'] = '==20.1.0'
        if pin_source == 'input':
            inputs['ddev-version'] = {'type': 'string', 'default': '==20.1.0'}
        else:
            # New jobs must inherit the workflow's existing pins too.
            del workflow['jobs'][next(iter(workflow['jobs']))]
        path.write_text(yaml.safe_dump(workflow, sort_keys=False))
        expected[filename] = revision

    result = ddev('validate', 'ci', '--sync')
    assert result.exit_code == 0, result.output
    for filename, revision in expected.items():
        workflow = yaml.safe_load((repository.path / '.github/workflows' / filename).read_text())
        for job in workflow['jobs'].values():
            assert job['uses'] == f'{TEST_WORKFLOW_PREFIX}{revision}'
            assert job['with']['ddev-version'] == ('==20.1.0' if pin_source == 'job' else '${{ inputs.ddev-version }}')

    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output


def test_ci_generator_preserves_partially_pinned_jobs(ddev, repository, config_file):
    config_file.model.repos['extras'] = str(repository.path)
    config_file.model.repo = 'extras'
    config_file.save()
    result = ddev('validate', 'ci', '--sync')
    assert result.exit_code == 0, result.output

    path = repository.path / '.github/workflows/test-all.yml'
    workflow = yaml.safe_load(path.read_text())
    workflow['on'] = workflow.pop(True)
    expected = {}
    for index, (job_id, job) in enumerate(workflow['jobs'].items()):
        revision = ('a' if index == 0 else 'b') * 40
        job['uses'] = f'{TEST_WORKFLOW_PREFIX}{revision}'
        version = None if index == 0 else '==20.1.0'
        if version is not None:
            job['with']['ddev-version'] = version
        expected[job_id] = (job['uses'], version)
    path.write_text(yaml.safe_dump(workflow, sort_keys=False))

    result = ddev('validate', 'ci', '--sync')
    assert result.exit_code == 0, result.output
    generated = yaml.safe_load(path.read_text())
    for job_id, (reference, version) in expected.items():
        job = generated['jobs'][job_id]
        assert job['uses'] == reference
        assert job['with'].get('ddev-version') == version

    result = ddev('validate', 'ci')
    assert result.exit_code == 0, result.output


@pytest.mark.parametrize(
    ('field', 'second_pin'),
    [('uses', 'release/next'), ('ddev-version', '==20.2.0'), ('ddev-version', None)],
)
def test_ci_generator_requires_a_choice_for_new_jobs_with_mixed_pins(field: str, second_pin: str | None):
    import click

    jobs = {
        'first': {'uses': f'{TEST_WORKFLOW_PREFIX}release/stable', 'with': {}},
        'second': {'uses': f'{TEST_WORKFLOW_PREFIX}release/stable', 'with': {}},
    }
    if field == 'uses':
        jobs['second']['uses'] = f'{TEST_WORKFLOW_PREFIX}{second_pin}'
    else:
        jobs['first']['with'][field] = '==20.1.0'
        if second_pin is not None:
            jobs['second']['with'][field] = second_pin
    workflow = {'jobs': jobs}

    reference, settings = _get_test_workflow_settings(workflow, 'second')
    assert reference == jobs['second']['uses']
    assert settings == jobs['second']['with']
    with pytest.raises(click.ClickException, match='Choose .*new job `new`'):
        _get_test_workflow_settings(workflow, 'new')
