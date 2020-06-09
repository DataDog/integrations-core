# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from semver import parse_version_info

from ...git import git_tag_list


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
