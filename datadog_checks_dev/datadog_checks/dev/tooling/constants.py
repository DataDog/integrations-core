# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import OrderedDict

import semver

CHANGELOG_LABEL_PREFIX = 'changelog/'
CHANGELOG_TYPE_NONE = 'no-changelog'
VERSION_BUMP = OrderedDict([
    ('Added', semver.bump_minor),
    ('Changed', semver.bump_major),
    ('Deprecated', semver.bump_minor),
    ('Fixed', semver.bump_patch),
    ('Removed', semver.bump_major),
    ('Security', semver.bump_minor),

    ('major', semver.bump_major),
    ('minor', semver.bump_minor),
    ('patch', semver.bump_patch),
    ('fix', semver.bump_patch),
    ('pre', semver.bump_prerelease),
    ('build', semver.bump_build),
])

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
