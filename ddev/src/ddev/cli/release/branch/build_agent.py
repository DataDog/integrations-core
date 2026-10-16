# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.cli.application import Application

BUILD_AGENT_YAML_PATH = '.gitlab/build_agent.yaml'
BUILD_AGENT_TEMPLATE_PATTERN = r'^\.build-agent-tpl:\n(?:[^\S\n].*(?:\n|$))*'
BUILD_AGENT_MAIN_BRANCH_PATTERN = r'^(\s+branch:\s+)main([^\S\n]*)$'
BUILD_AGENT_TEMPLATE_REGEX = re.compile(BUILD_AGENT_TEMPLATE_PATTERN, re.MULTILINE)
BUILD_AGENT_MAIN_BRANCH_REGEX = re.compile(BUILD_AGENT_MAIN_BRANCH_PATTERN, re.MULTILINE)
BUILD_AGENT_COMPARE_TO_MASTER_REGEX = re.compile(r'^(\s+compare_to:\s+refs/heads/)master[^\S\n]*$', re.MULTILINE)

DATADOG_AGENT_REPO_URL = 'https://github.com/DataDog/datadog-agent.git'


def agent_branch_exists(branch_name: str) -> bool:
    """Return ``True`` if ``branch_name`` exists in ``DataDog/datadog-agent``."""
    result = subprocess.run(
        ['git', 'ls-remote', '--exit-code', '--heads', DATADOG_AGENT_REPO_URL, branch_name],
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def find_build_agent_template_main_branch_matches(content: str) -> list[re.Match[str]]:
    template_match = BUILD_AGENT_TEMPLATE_REGEX.search(content)
    if template_match is None:
        return []
    return list(BUILD_AGENT_MAIN_BRANCH_REGEX.finditer(template_match.group(0)))


def replace_build_agent_template_main_branch(content: str, branch_name: str) -> tuple[str, int]:
    template_match = BUILD_AGENT_TEMPLATE_REGEX.search(content)
    if template_match is None:
        return content, 0

    def replacement(match: re.Match[str]) -> str:
        return f'{match.group(1)}{branch_name}{match.group(2)}'

    updated_template, replacement_count = BUILD_AGENT_MAIN_BRANCH_REGEX.subn(
        replacement, template_match.group(0), count=1
    )
    if replacement_count == 0:
        return content, 0

    updated_content = content[: template_match.start()] + updated_template + content[template_match.end() :]
    return updated_content, replacement_count


@dataclass
class BuildAgentModification:
    """build_agent.yaml content as it goes through each modification, with what each one did."""

    content: str
    updates: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def point_compare_to_at_release_branch(modification: BuildAgentModification, branch_name: str) -> None:
    content, replacement_count = BUILD_AGENT_COMPARE_TO_MASTER_REGEX.subn(
        lambda match: f'{match.group(1)}{branch_name}', modification.content
    )
    if replacement_count:
        modification.content = content
        modification.updates.append(f'compare dependency changes against `{branch_name}`')


def point_template_at_agent_branch(modification: BuildAgentModification, branch_name: str) -> None:
    matches = find_build_agent_template_main_branch_matches(modification.content)
    if not matches:
        return

    branch_exists = agent_branch_exists(branch_name)
    if len(matches) > 1:
        modification.errors.append(
            f'Expected exactly one `.build-agent-tpl` branch pointing to `main` in `{BUILD_AGENT_YAML_PATH}`; '
            f'found {len(matches)}.'
        )
    if not branch_exists:
        modification.warnings.append(
            f'Unable to verify that agent branch `{branch_name}` exists in `DataDog/datadog-agent`. '
            f'Leaving `{BUILD_AGENT_YAML_PATH}` pointing to `main`. '
            f'Re-dispatch `update-build-agent-yaml.yml` (or re-run `ddev release branch tag`) '
            f'once the upstream branch exists.'
        )
    if len(matches) == 1 and branch_exists:
        modification.content, _ = replace_build_agent_template_main_branch(modification.content, branch_name)
        modification.updates.append(f'use Agent branch `{branch_name}`')


def ensure_build_agent_yaml_updated(app: Application, branch_name: str) -> bool:
    """Update build_agent.yaml on a new release branch and return whether the file changed.

    The `compare_to` baseline always moves to the release branch, so branches cut from it measure their
    dependency changes against the release branch instead of master. The Agent branch pointer stays on `main`
    when the matching `DataDog/datadog-agent` branch does not exist yet, leaving it to the recovery path
    (`ddev release branch tag` -> `update-build-agent-yaml.yml`).
    """
    from ddev.utils.fs import Path

    build_agent_yaml = Path(BUILD_AGENT_YAML_PATH)

    if not build_agent_yaml.exists():
        app.display_warning(f'Warning: {build_agent_yaml} not found')
        return False

    with open(build_agent_yaml, 'r') as f:
        content = f.read()

    modification = BuildAgentModification(content)
    for modify in (point_compare_to_at_release_branch, point_template_at_agent_branch):
        modify(modification, branch_name)

    for warning in modification.warnings:
        app.display_warning(warning)
    if modification.errors:
        app.abort('\n'.join(modification.errors))
        return False
    if not modification.updates:
        return False

    with open(build_agent_yaml, 'w') as f:
        f.write(modification.content)

    for update in modification.updates:
        app.display_success(f'Updated build_agent.yaml to {update}')
    return True
