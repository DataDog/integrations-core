# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os

import requests


API_URL = 'https://api.github.com'
PR_ENDPOINT = API_URL + '/repos/DataDog/integrations-core/pulls/{}'

CHANGELOG_LABEL_PREFIX = 'changelog/'
CHANGELOG_TYPE_NONE = 'no-changelog'


def get_auth_info():
    """
    See if a personal access token was passed
    """
    user = os.environ.get('DATADOG_GITHUB_API_USER')
    tok = os.environ.get('DATADOG_GITHUB_API_TOKEN')
    if user and tok:
        return (user, tok)
    return None


def get_changelog_types(pr_payload):
    """
    Fetch the labels from the PR and process the ones related to the changelog.
    """
    changelog_labels = []
    for l in pr_payload.get('labels', []):
        name = l.get('name')
        if name.startswith(CHANGELOG_LABEL_PREFIX):
            # only add the name, e.g. for `changelog/Added` it's just `Added`
            changelog_labels.append(name.split(CHANGELOG_LABEL_PREFIX)[1])

    return changelog_labels


def get_pr(pr_num):
    """
    Get the payload for the given PR number. Let exceptions bubble up.
    """
    response = requests.get(PR_ENDPOINT.format(pr_num), auth=get_auth_info())
    return response.json()


def from_contributor(pr_payload):
    """
    If the PR comes from a fork, we can safely assumed it's from an
    external contributor.
    """
    return pr_payload.get('head', {}).get('repo', {}).get('fork') is True
