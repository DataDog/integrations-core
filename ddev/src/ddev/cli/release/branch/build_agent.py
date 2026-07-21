# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

import re
import subprocess
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.cli.application import Application

BUILD_AGENT_YAML_PATH = '.gitlab/build_agent.yaml'
BUILD_AGENT_TEMPLATE_PATTERN = r'^\.build-agent-tpl:\n(?:[^\S\n].*(?:\n|$))*'
BUILD_AGENT_MAIN_BRANCH_PATTERN = r'^(\s+branch:\s+)main([^\S\n]*)$'
BUILD_AGENT_TEMPLATE_REGEX = re.compile(BUILD_AGENT_TEMPLATE_PATTERN, re.MULTILINE)
BUILD_AGENT_MAIN_BRANCH_REGEX = re.compile(BUILD_AGENT_MAIN_BRANCH_PATTERN, re.MULTILINE)

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


def ensure_build_agent_yaml_updated(app: Application, branch_name: str) -> bool:
    """Update build_agent.yaml to point to the release branch when it still targets main.

    Returns False without modifying the file when the matching ``DataDog/datadog-agent``
    branch does not exist yet, so callers can leave ``main`` in place for the recovery
    path (``ddev release branch tag`` -> ``update-build-agent-yaml.yml``) to run later.
    """
    from ddev.utils.fs import Path

    build_agent_yaml = Path(BUILD_AGENT_YAML_PATH)

    if not build_agent_yaml.exists():
        app.display_warning(f'Warning: {build_agent_yaml} not found')
        return False

    with open(build_agent_yaml, 'r') as f:
        content = f.read()

    matches = find_build_agent_template_main_branch_matches(content)
    if not matches:
        return False
    if len(matches) > 1:
        app.abort(
            f'Expected exactly one `.build-agent-tpl` branch pointing to `main` in `{BUILD_AGENT_YAML_PATH}`; '
            f'found {len(matches)}.'
        )
        return False

    if not agent_branch_exists(branch_name):
        app.display_warning(
            f'Unable to verify that agent branch `{branch_name}` exists in `DataDog/datadog-agent`. '
            f'Leaving `{BUILD_AGENT_YAML_PATH}` pointing to `main`. '
            f'Re-dispatch `update-build-agent-yaml.yml` (or re-run `ddev release branch tag`) '
            f'once the upstream branch exists.'
        )
        return False

    updated_content, replacement_count = replace_build_agent_template_main_branch(content, branch_name)
    assert replacement_count == 1

    with open(build_agent_yaml, 'w') as f:
        f.write(updated_content)

    app.display_success(f'Updated build_agent.yaml file to use Agent branch: {branch_name}')
    return True
