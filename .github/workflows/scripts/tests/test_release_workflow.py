from pathlib import Path
from typing import Any

import yaml

WORKFLOWS_DIR = Path(__file__).resolve().parents[2]


def load_workflow(name: str) -> dict[str, Any]:
    with open(WORKFLOWS_DIR / name, encoding='utf-8') as workflow_file:
        return yaml.safe_load(workflow_file)


def get_step(steps: list[dict[str, Any]], name: str) -> dict[str, Any]:
    return next(step for step in steps if step.get('name') == name)


def test_release_tag_push_uses_source_sts_token() -> None:
    workflow = load_workflow('release-dispatch.yml')
    steps = workflow['jobs']['prepare']['steps']

    token_step = get_step(steps, 'Get source tag token via dd-octo-sts')
    checkout_step = get_step(steps, 'Checkout source repo')

    assert steps.index(token_step) < steps.index(checkout_step)
    assert token_step['with'] == {
        'scope': "DataDog/${{ inputs.source-repo || 'integrations-core' }}",
        'policy': 'self.release.tag-push',
    }
    assert checkout_step['with']['token'] == '${{ steps.source-octo-sts.outputs.token }}'
    assert checkout_step['with']['persist-credentials'] is True


def test_release_workflows_use_read_only_default_token() -> None:
    dispatch = load_workflow('release-dispatch.yml')
    trigger = load_workflow('release-trigger.yml')

    assert dispatch['permissions']['contents'] == 'read'
    assert trigger['jobs']['dispatch']['permissions']['contents'] == 'read'


def test_wheel_dispatch_keeps_destination_sts_token() -> None:
    workflow = load_workflow('release-dispatch.yml')
    steps = workflow['jobs']['dispatch']['steps']
    token_step = get_step(steps, 'Get GitHub token via dd-octo-sts')

    assert token_step['with']['scope'] == 'DataDog/agent-integration-wheels-release'
    assert token_step['with']['policy'] == "${{ inputs.source-repo || 'integrations-core' }}.dispatch-wheel-builds"
