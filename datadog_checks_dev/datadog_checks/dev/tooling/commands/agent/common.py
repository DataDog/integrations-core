# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from semver import parse_version_info

from ...constants import get_agent_release_requirements
from ...git import git_show_file, git_tag_list
from ...release import DATADOG_PACKAGE_PREFIX, get_folder_name, get_package_name
from ...utils import parse_agent_req_file


def get_agent_tags(since, to):
    """
    Return a list of tags from integrations-core representing an Agent release,
    sorted by more recent first.
    """
    agent_tags = sorted(parse_version_info(t) for t in git_tag_list(r'^\d+\.\d+\.\d+$'))

    # default value for `to` is the latest tag
    if to:
        to = parse_version_info(to)
    else:
        to = agent_tags[-1]

    since = parse_version_info(since)

    # filter out versions according to the interval [since, to]
    agent_tags = [t for t in agent_tags if since <= t <= to]

    # reverse so we have descendant order
    return [str(t) for t in reversed(agent_tags)]


def get_changes_per_agent(since, to):
    """
    Return integration versions groups by Agent versions.
    For each version, we also get a boolean indicating if the version has breaking changes.

    Structure:

    ```
    {
        '<AGENT_VERSION>': {
            '<INTEGRATION_NAME>': ('<INTEGRATION_VERSION>', <IS_BREAKING_CHANGE>)
        }
    }
    ```

    Example output:

    ```python
    {
        '7.20.0': {
            'snmp': ('1.9.1', False)
        }
    }
    ```
    """
    agent_tags = get_agent_tags(since, to)
    # store the changes in a mapping {agent_version --> {check_name --> current_version}}
    changes_per_agent = {}
    # to keep indexing easy, we run the loop off-by-one
    for i in range(1, len(agent_tags)):
        req_file_name = os.path.basename(get_agent_release_requirements())
        current_tag = agent_tags[i - 1]
        # Requirements for current tag
        file_contents = git_show_file(req_file_name, current_tag)
        catalog_now = parse_agent_req_file(file_contents)
        # Requirements for previous tag
        file_contents = git_show_file(req_file_name, agent_tags[i])
        catalog_prev = parse_agent_req_file(file_contents)

        changes_per_agent[current_tag] = {}

        for name, ver in catalog_now.items():
            # at some point in the git history, the requirements file erroneusly
            # contained the folder name instead of the package name for each check,
            # let's be resilient
            old_ver = (
                catalog_prev.get(name)
                or catalog_prev.get(get_folder_name(name))
                or catalog_prev.get(get_package_name(name))
            )

            # normalize the package name to the check_name
            if name.startswith(DATADOG_PACKAGE_PREFIX):
                name = get_folder_name(name)

            if old_ver and old_ver != ver:
                # determine whether major version changed
                breaking = old_ver.split('.')[0] < ver.split('.')[0]
                changes_per_agent[current_tag][name] = (ver, breaking)
            elif not old_ver:
                # New integration
                changes_per_agent[current_tag][name] = (ver, False)
    return changes_per_agent
