# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
CHANGELOG_LABEL_PREFIX = 'changelog/'
CHANGELOG_TYPE_NONE = 'no-changelog'
CHANGELOG_TYPES = [
    'Added',
    'Changed',
    'Deprecated',
    'Fixed',
    'Removed',
    'Security',
]

# The checks requirement file used by the agent
AGENT_REQ_FILE = 'requirements-agent-release.txt'

AGENT_V5_ONLY = {
    'agent_metrics',
    'docker_daemon',
    'kubernetes',
    'ntp',
}

# If a file changes in a PR with any of these file extensions,
# a test will run against the check containing the file
TESTABLE_FILE_EXTENSIONS = (
    '.py',
    '.ini',
    '.in',
    '.txt',
)


ROOT = ''


def get_root():
    return ROOT


def set_root(path):
    global ROOT
    ROOT = path
