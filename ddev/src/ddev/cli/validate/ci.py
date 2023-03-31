# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddev.cli.application import Application


@click.command()
@click.option('--sync', is_flag=True, help='Update the CI configuration')
@click.pass_context
def ci(ctx: click.Context, sync: bool):
    """Validate CI infrastructure configuration."""
    import hashlib
    import json

    import yaml
    from datadog_checks.dev.tooling.commands.validate.ci import ci as legacy_validation

    from ddev.utils.scripts.ci_matrix import construct_job_matrix, get_all_targets

    app: Application = ctx.obj
    is_core = app.repo.name == 'core'
    test_workflow = (
        './.github/workflows/test-target.yml'
        if app.repo.name == 'core'
        else 'DataDog/integrations-core/.github/workflows/test-target.yml@master'
    )
    jobs_workflow_path = app.repo.path / '.github' / 'workflows' / 'test-all.yml'
    original_jobs_workflow = jobs_workflow_path.read_text() if jobs_workflow_path.is_file() else ''

    jobs = {}
    for data in construct_job_matrix(app.repo.path, get_all_targets(app.repo.path)):
        python_restriction = data.get('python-support', '')
        config = {
            'job-name': data['name'],
            'target': data['target'],
            'platform': data['platform'],
            'runner': json.dumps(data['runner'], separators=(',', ':')),
            'repo': '${{ inputs.repo }}',
            # Options
            'python-version': '${{ inputs.python-version }}',
            'standard': '${{ inputs.standard }}',
            'latest': '${{ inputs.latest }}',
            'agent-image': '${{ inputs.agent-image }}',
            'agent-image-py2': '${{ inputs.agent-image-py2 }}',
            'agent-image-windows': '${{ inputs.agent-image-windows }}',
            'agent-image-windows-py2': '${{ inputs.agent-image-windows-py2 }}',
            'test-py2': '2' in python_restriction if python_restriction else '${{ inputs.test-py2 }}',
            'test-py3': '3' in python_restriction if python_restriction else '${{ inputs.test-py3 }}',
        }
        if is_core:
            config.update(
                {
                    'minimum-base-package': '${{ inputs.minimum-base-package }}',
                }
            )
        else:
            config.update(
                {
                    'setup-env-vars': '${{ inputs.setup-env-vars }}',
                }
            )

        # Prevent redundant job hierarchy names at the bottom of pull requests and also satisfy the naming requirements:
        # https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_id
        #
        # We want the job ID to be unique but also small so it displays concisely on the bottom of pull requests
        job_id = hashlib.sha256(config['job-name'].encode('utf-8')).hexdigest()[:7]
        job_id = f'j{job_id}'

        jobs[job_id] = {'uses': test_workflow, 'with': config, 'secrets': 'inherit'}

    jobs_component = yaml.safe_dump({'jobs': jobs}, default_flow_style=False, sort_keys=False)

    # Enforce proper string types
    for field in (
        'repo',
        'python-version',
        'setup-env-vars',
        'agent-image',
        'agent-image-py2',
        'agent-image-windows',
        'agent-image-windows-py2',
    ):
        jobs_component = jobs_component.replace(f'${{{{ inputs.{field} }}}}', f'"${{{{ inputs.{field} }}}}"')

    manual_component = original_jobs_workflow.split('jobs:')[0].strip()
    expected_jobs_workflow = f'{manual_component}\n\n{jobs_component}'

    if original_jobs_workflow != expected_jobs_workflow:
        if sync:
            jobs_workflow_path.write_text(expected_jobs_workflow)
        else:
            app.abort('CI configuration is not in sync, try again with the `--sync` flag')

    ctx.invoke(legacy_validation, fix=sync)
