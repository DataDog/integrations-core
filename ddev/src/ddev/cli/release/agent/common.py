# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddev.repo.core import Repository

    AgentChangelog = dict[str, dict[str, tuple[str, bool, bool]]]

DATADOG_PACKAGE_PREFIX = 'datadog-'
UNRELEASED_INTEGRATIONS_CONFIG = '/overrides/release/agent/unreleased-integrations'


def get_agent_tags(repo: Repository, since: str, to: str) -> list[str]:
    """
    Return a list of tags from integrations-core representing an Agent release,
    sorted by more recent first.
    """
    from packaging.version import parse as parse_version

    agent_tags = sorted(parse_version(t) for t in repo.git.filter_tags(r'^\d+\.\d+\.\d+$'))

    # default value for `to` is the latest tag
    to_version = parse_version(to) if to else agent_tags[-1]
    since_version = parse_version(since)

    # filter out versions according to the interval [since, to]
    agent_tags = [t for t in agent_tags if since_version <= t <= to_version]

    # reverse so we have descendant order
    return [str(t) for t in reversed(agent_tags)]


def get_changes_per_agent(repo: Repository, since: str, to: str) -> AgentChangelog:
    """
    Return integration versions groups by Agent versions.
    For each version, we also get booleans indicating if the integration is new
    and if the version has breaking changes.

    Structure:

    ```
    {
        '<AGENT_VERSION>': {
            '<INTEGRATION_NAME>': ('<INTEGRATION_VERSION>', <IS_NEW>, <IS_BREAKING_CHANGE>)
        }
    }
    ```

    Example output:

    ```python
    {
        '7.20.0': {
            'snmp': ('1.9.1', False, False)
        }
    }
    ```
    """
    agent_tags = get_agent_tags(repo, since, to)
    # store the changes in a mapping {agent_version --> {check_name --> (current_version, is_new, is_breaking_change)}}
    changes_per_agent: AgentChangelog = {}
    # to keep indexing easy, we run the loop off-by-one
    for i in range(1, len(agent_tags)):
        req_file_name = repo.agent_release_requirements.name
        current_tag = agent_tags[i - 1]
        # Requirements for current tag
        file_contents = repo.git.show_file(req_file_name, current_tag)
        catalog_now = parse_agent_req_file(file_contents)
        # Requirements for previous tag
        file_contents = repo.git.show_file(req_file_name, agent_tags[i])
        catalog_prev = parse_agent_req_file(file_contents)

        catalog_now = exclude_unreleased_integrations(repo, normalize_catalog(catalog_now), current_tag)
        catalog_prev = exclude_unreleased_integrations(repo, normalize_catalog(catalog_prev), agent_tags[i])

        changes_per_agent[current_tag] = {}

        for name, ver in catalog_now.items():
            old_ver = catalog_prev.get(name)

            if old_ver and old_ver != ver:
                # determine whether major version changed
                breaking = old_ver.split('.')[0] < ver.split('.')[0]
                changes_per_agent[current_tag][name] = (ver, False, breaking)
            elif not old_ver:
                # New integration
                changes_per_agent[current_tag][name] = (ver, True, False)
    return changes_per_agent


# at some point in the git history, the requirements file erroneously
# contained the folder name instead of the package name for each check,
# let's be resilient by normalizing all entries to be folder names
def normalize_catalog(catalog: dict[str, str]) -> dict[str, str]:
    return {normalize_package_name(k): v for k, v in catalog.items()}


def exclude_unreleased_integrations(repo: Repository, catalog: dict[str, str], agent_version: str) -> dict[str, str]:
    skipped_integrations = get_unreleased_integrations(repo, agent_version)
    if not skipped_integrations:
        return catalog
    return {
        name: version for name, version in catalog.items() if normalize_package_name(name) not in skipped_integrations
    }


def get_unreleased_integrations(repo: Repository, agent_version: str) -> set[str]:
    unreleased_integrations = repo.config.get(UNRELEASED_INTEGRATIONS_CONFIG, default={})
    by_integration = unreleased_integrations.get('by-integration', {})
    by_agent_version_range = unreleased_integrations.get('by-agent-version-range', {})

    skipped_integrations = {
        normalize_package_name(name) for name, versions in by_integration.items() if agent_version in versions
    }
    for version_range, integration_names in by_agent_version_range.items():
        if agent_version_in_range(agent_version, version_range):
            skipped_integrations.update(normalize_package_name(name) for name in integration_names)

    return skipped_integrations


def agent_version_in_range(agent_version: str, version_range: str) -> bool:
    from packaging.version import parse as parse_version

    parts = version_range.split('..', 1)
    if len(parts) != 2:
        raise ValueError(
            f"Invalid version range {version_range!r} in "
            f"{UNRELEASED_INTEGRATIONS_CONFIG}/by-agent-version-range; "
            "expected format: 'START..END'"
        )
    start, end = parts
    version = parse_version(agent_version)
    start_version = parse_version(start)
    end_version = parse_version(end)

    return start_version <= version <= end_version


def normalize_package_name(name: str) -> str:
    """
    Given a Python package name for a check, return the corresponding folder
    name in the git repo.
    """
    if name not in ('datadog-checks-base', 'datadog-checks-downloader', 'datadog-checks-dependency-provider'):
        name = name.removeprefix(DATADOG_PACKAGE_PREFIX)

    return name.replace('-', '_')


def parse_agent_req_file(contents: str) -> dict[str, str]:
    """
    Returns a dictionary mapping {check-package-name --> pinned_version} from the
    given file contents. We can assume lines are in the form:

        datadog-active-directory==1.1.1; sys_platform == 'win32'

    """
    catalog = {}
    for line in contents.splitlines():
        toks = line.split('==', 1)
        if len(toks) != 2 or not toks[0] or not toks[1]:
            # if we get here, the requirements file is garbled but let's stay
            # resilient
            continue

        name, other = toks
        version = other.split(';')
        catalog[name] = version[0]

    return catalog
