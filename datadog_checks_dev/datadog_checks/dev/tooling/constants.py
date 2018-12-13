# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
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
    ('rc', lambda v: semver.bump_prerelease(v, 'rc')),
    ('pre', lambda v: semver.bump_prerelease(v, 'pre')),
    ('alpha', lambda v: semver.bump_prerelease(v, 'alpha')),
    ('beta', lambda v: semver.bump_prerelease(v, 'beta')),
])

# The requirements file listing integrations to be included in the Agent package
AGENT_RELEASE_REQ_FILE = 'requirements-agent-release.txt'
# The requirements file listing dependencies needed by the embedded Python environment
AGENT_REQUIREMENTS = os.path.join(
    'datadog_checks_base', 'datadog_checks', 'base', 'data', 'agent_requirements.in'
)
AGENT_V5_ONLY = {
    'agent_metrics',
    'docker_daemon',
    'kubernetes',
    'ntp',
}

BETA_PACKAGES = {
    'datadog_checks_dev',
}

NOT_CHECKS = {
    'datadog_checks_dev',
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
