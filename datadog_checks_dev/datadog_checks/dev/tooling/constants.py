# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import semver

CHANGELOG_LABEL_PREFIX = 'changelog/'
CHANGELOG_TYPE_NONE = 'no-changelog'
INTEGRATION_REPOS = [
    'integrations-core',
    'integrations-extras',
    'integrations-internal',
]

REPO_OPTIONS_MAP = {
    '--core': 'core',
    '-c': 'core',
    '--extras': 'extras',
    '-e': 'extras',
    '--agent': 'agent',
    '-a': 'agent',
    '--marketplace': 'marketplace',
    '-m': 'marketplace',
    '--here': 'here',
    '-x': 'here',
}

REPO_CHOICES = {
    'core': 'integrations-core',
    'extras': 'integrations-extras',
    'internal': 'integrations-internal',
    'agent': 'datadog-agent',
    'marketplace': 'marketplace',
}

VERSION_BUMP = {
    'Added': semver.bump_minor,
    'Changed': semver.bump_major,
    'Deprecated': semver.bump_minor,
    'Fixed': semver.bump_patch,
    'Removed': semver.bump_major,
    'Security': semver.bump_minor,
    'major': semver.bump_major,
    'minor': semver.bump_minor,
    'patch': semver.bump_patch,
    'fix': semver.bump_patch,
    'rc': lambda v: semver.bump_prerelease(v, 'rc'),
    'alpha': lambda v: semver.bump_prerelease(v, 'alpha'),
    'beta': lambda v: semver.bump_prerelease(v, 'beta'),
}

CHANGELOG_TYPES_ORDERED = ['Added', 'Fixed', 'Security', 'Changed', 'Deprecated', 'Removed']

AGENT_V5_ONLY = {'agent_metrics', 'docker_daemon', 'go-metro', 'kubernetes', 'ntp'}

BETA_PACKAGES = {'datadog_checks_dev', 'datadog_checks_downloader'}

NOT_CHECKS = {'datadog_checks_dev'}

# Some integrations do not have an associated tile, mostly system integrations
NOT_TILES = [
    'agent_metrics',
    'directory',
    'disk',
    'dns_check',
    'go-metro',
    'go_expvar',
    'http_check',
    'kube_dns',
    'kube_proxy',
    'kubelet',
    'network',
    'nfsstat',
    'ntp',
    'process',
    'riakcs',
    'statsd',
    'system_core',
    'system_swap',
    'tcp_check',
    'win32_event_log',
    'wmi_check',
]

# If a file changes in a PR with any of these file extensions,
# a test will run against the check containing the file
TESTABLE_FILE_PATTERNS = ('*.py', '*.ini', '*.in', '*.txt', '*.yml', '*.yaml', '**/tests/*')
NON_TESTABLE_FILES = ('auto_conf.yaml', 'agent_requirements.in')

REQUIREMENTS_IN = 'requirements.in'

ROOT = ''


def get_root():
    return ROOT


def set_root(path):
    global ROOT
    ROOT = path


def get_agent_release_requirements():
    """
    Return the full path to the requirements file listing integrations to be
    included in the Agent package
    """
    return os.path.join(get_root(), 'requirements-agent-release.txt')


def get_agent_requirements():
    """
    Return the full path to the requirements file listing all the dependencies
    needed by the embedded Python environment
    """
    return os.path.join(get_root(), 'datadog_checks_base', 'datadog_checks', 'base', 'data', 'agent_requirements.in')


def get_agent_integrations_file():
    """
    Return the full path to the file containing the full list of integrations
    shipped with any Datadog Agent release.
    """
    return os.path.join(get_root(), 'AGENT_INTEGRATIONS.md')


def get_agent_changelog():
    """
    Return the full path to the file containing the list of integrations that
    have changed with any Datadog Agent release.
    """
    return os.path.join(get_root(), 'AGENT_CHANGELOG.md')


def get_integration_changelog(check):
    """
    Return the full path to the integration changelog.
    """
    return os.path.join(get_root(), check, 'CHANGELOG.md')


def get_license_attribution_file():
    return os.path.join(get_root(), 'LICENSE-3rdparty.csv')
