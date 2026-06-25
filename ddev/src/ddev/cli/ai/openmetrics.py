# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from pathlib import Path

    from ddev.cli.application import Application

# Wall-clock budget for the whole flow.
DEFAULT_TIMEOUT = 3600.0

# Files the flow is expected to produce, relative to the integration directory.
# Used only for the final summary so the user can see at a glance what landed.
EXPECTED_ARTIFACTS = (
    'datadog_checks/{name}/metrics.yaml',
    'metadata.csv',
    'datadog_checks/{name}/check.py',
    'assets/configuration/spec.yaml',
    'datadog_checks/{name}/data/conf.yaml.example',
    'tests/conftest.py',
    'tests/test_unit.py',
    'tests/test_integration.py',
    'tests/test_e2e.py',
    'tests/docker',
    'tests/fixtures/metrics.txt',
)


def _normalize(display_name: str) -> str:
    """Derive the snake_case integration name from the display name."""
    return re.sub(r'[^a-z0-9]+', '_', display_name.lower()).strip('_')


def _flow_phase_ids(flow_yaml: Path) -> list[str]:
    """The phases the flow schedules, in order."""
    import yaml

    flow = yaml.safe_load(flow_yaml.read_text(encoding='utf-8'))
    return [entry['phase'] for entry in flow.get('flow', [])]


def _incomplete_phases(checkpoint_path: Path, flow_yaml: Path) -> list[str]:
    """Scheduled phases that did not reach 'success' (e.g. on timeout)."""
    from ddev.ai.runtime.checkpoints import CheckpointManager

    phase_ids = _flow_phase_ids(flow_yaml)
    if not checkpoint_path.exists():
        return phase_ids
    successful = CheckpointManager(checkpoint_path).successful_phases()
    return [pid for pid in phase_ids if pid not in successful]


def _report_artifacts(app: Application, integration_dir: Path) -> None:
    """Print which expected artifacts the flow produced."""
    name = integration_dir.name
    app.display_header('Generated artifacts')
    for rel in EXPECTED_ARTIFACTS:
        path = integration_dir / rel.format(name=name)
        marker = '✓' if path.exists() else '✗'
        app.display_info(f'  {marker} {path.relative_to(integration_dir.parent)}')


@click.command('openmetrics', short_help='Scaffold an OpenMetrics integration with AI')
@click.argument('display_name')
@click.option(
    '--endpoint',
    required=True,
    help='OpenMetrics endpoint URL to inspect, e.g. `http://localhost:9090/metrics`.',
)
@click.option(
    '--docker-path',
    required=True,
    help='Path to a `tests/docker` directory copied into the generated integration for E2E tests.',
)
@click.option(
    '--prd',
    required=True,
    help='Path to a product requirements document (.md) with the team-specific requirements the '
    'integration must satisfy (e.g. metrics to drop, forced config defaults).',
)
@click.option('--force', is_flag=True, help='Overwrite the integration directory if it already exists.')
@click.option(
    '--resume',
    is_flag=True,
    help='Resume the previous run for this integration, skipping phases that already completed '
    'successfully. Requires an existing run and is mutually exclusive with `--force`.',
)
@click.option(
    '--timeout',
    type=float,
    default=DEFAULT_TIMEOUT,
    show_default=True,
    help='Maximum wall-clock seconds for the whole flow.',
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Stream the full agent conversation (prompts, responses, tool calls).',
)
@click.pass_obj
def openmetrics(
    app: Application,
    *,
    display_name: str,
    endpoint: str,
    docker_path: str,
    prd: str,
    force: bool,
    resume: bool,
    timeout: float,
    verbose: bool,
):
    """Scaffold an OpenMetrics integration for DISPLAY_NAME using an AI agent flow.

    DISPLAY_NAME is the technology's display name (e.g. `KrakenD`); the agent
    derives the snake_case package name and metric prefix from it.
    """
    import shutil
    import warnings
    from pathlib import Path

    import ddev.ai
    from ddev.cli.ai.console_logger import build_console_callbacks

    if timeout <= 0:
        app.abort('`--timeout` must be greater than 0.')

    api_key = app.config.ai.anthropic_api_key
    if not api_key:
        app.abort(
            'No Anthropic API key found. Set `ai.anthropic_api_key` in your ddev config '
            '(see `ddev config`), or export `DD_ANTHROPIC_API_KEY` / `ANTHROPIC_API_KEY`.'
        )

    docker_source = Path(docker_path).expanduser().resolve()
    if not docker_source.is_dir():
        app.abort(f'`--docker-path` {docker_source} is not a directory. Point it at a `tests/docker` directory.')

    prd_path = Path(prd).expanduser().resolve()
    if not prd_path.is_file():
        app.abort(f'`--prd` file {prd_path} does not exist. Provide a product requirements document.')
    prd_content = prd_path.read_text(encoding='utf-8').strip()
    if not prd_content:
        app.abort(
            f'`--prd` file {prd_path} is empty. Write the requirements in it; if there are genuinely '
            'none, state that explicitly.'
        )

    integration_name = _normalize(display_name)
    if not integration_name:
        app.abort(f'Could not derive an integration name from {display_name!r}.')

    if resume and force:
        app.abort('`--resume` and `--force` are mutually exclusive: resume keeps prior work, force deletes it.')

    repo_path = Path(app.repo.path)
    integration_dir = repo_path / integration_name

    # TODO: discover the existing flow.yaml
    flow_yaml = Path(ddev.ai.__file__).resolve().parent / 'flows' / 'openmetrics' / 'flow.yaml'
    if not flow_yaml.is_file():
        app.abort(f'Flow definition not found: {flow_yaml}')

    run_dir = repo_path / '.ddev' / 'ai-runs' / integration_name
    checkpoint_path = run_dir / 'checkpoints.yaml'

    if resume:
        if not checkpoint_path.exists():
            app.abort(
                f"No previous run found for '{integration_name}' at {run_dir}. "
                'Run without `--resume` to start a fresh build.'
            )
        app.display_warning(
            'Resuming the previous run: phases that already completed are skipped, and the '
            'interrupted phase restarts — it will reconcile any partially written files.'
        )
    else:
        if integration_dir.exists():
            if not force:
                app.abort(
                    f"Integration '{integration_name}' already exists at {integration_dir}. "
                    'Pass `--force` to overwrite it.'
                )
            shutil.rmtree(integration_dir)
            app.display_warning(f'Removed existing {integration_dir} (--force).')
        if run_dir.exists():
            shutil.rmtree(run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)

    app.display_info(f'Technology:    {display_name}  (-> integration: {integration_name})')
    app.display_info(f'Endpoint:      {endpoint}')
    app.display_info(f'Docker source: {docker_source}')
    app.display_info(f'PRD:           {prd_path}')
    app.display_info(f'Timeout:       {timeout:.0f}s')
    app.display_info(f'Output repo:   {repo_path}')
    app.display_info(f'Run artifacts: {run_dir}')

    import anthropic

    from ddev.ai.runtime.orchestrator import PhaseOrchestrator
    from ddev.ai.tools.fs.file_access_policy import FileAccessPolicy

    orchestrator = PhaseOrchestrator(
        flow_yaml_path=flow_yaml,
        checkpoint_path=checkpoint_path,
        runtime_variables={
            'endpoint_url': endpoint,
            'integration': display_name,
            'docker_source_path': str(docker_source),
            'prd': prd_content,
        },
        agent_clients={'anthropic': anthropic.AsyncAnthropic(api_key=api_key)},
        file_access_policy=FileAccessPolicy(write_root=repo_path),
        callbacks=build_console_callbacks(app, verbose=verbose or app.verbose, run_dir=run_dir),
        resume=resume,
        max_timeout=timeout,
    )

    try:
        # Run from the repo root.
        with app.repo.path.as_cwd(), warnings.catch_warnings():
            warnings.filterwarnings('ignore', message='^Pydantic serializer warnings', module=r'pydantic\.main')
            orchestrator.run()
    except Exception as e:
        app.display_error(f'Pipeline failed: {type(e).__name__}: {e}')
        if app.verbosity > 0:
            import traceback

            app.display_error(traceback.format_exc())
        if orchestrator.failed_phase:
            app.display_error(f'  failed phase: {orchestrator.failed_phase}')
        app.display_warning('Re-run with `--resume` to retry from the failed phase; completed phases are skipped.')
        app.abort(f'Run artifacts saved at {run_dir}.')

    incomplete = _incomplete_phases(checkpoint_path, flow_yaml)
    if incomplete:
        app.display_error(f"Pipeline incomplete — these phases did not reach 'success': {', '.join(incomplete)}")
        app.display_warning(
            f'The run likely hit the {timeout:.0f}s budget; raise `--timeout` and re-run with `--resume`.'
        )
        _report_artifacts(app, integration_dir)
        app.abort(f'Run artifacts saved at {run_dir}.')

    app.display_success(f"Integration '{integration_name}' generated.")
    _report_artifacts(app, integration_dir)
