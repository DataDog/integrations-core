# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import re

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
    'integrations-internal-core': 'integrations-internal-core',
}

VERSION_BUMP = {
    'added': semver.bump_minor,
    'changed': semver.bump_major,
    'deprecated': semver.bump_minor,
    'fixed': semver.bump_patch,
    'removed': semver.bump_major,
    'security': semver.bump_minor,
    'major': semver.bump_major,
    'minor': semver.bump_minor,
    'patch': semver.bump_patch,
    'fix': semver.bump_patch,
    'rc': lambda v: semver.bump_prerelease(v, 'rc'),
    'alpha': lambda v: semver.bump_prerelease(v, 'alpha'),
    'beta': lambda v: semver.bump_prerelease(v, 'beta'),
}

CHANGELOG_TYPES_ORDERED = ['Removed', 'Changed', 'Security', 'Deprecated', 'Added', 'Fixed']

AGENT_V5_ONLY = {'agent_metrics', 'docker_daemon', 'go-metro', 'kubernetes', 'ntp'}

BETA_PACKAGES = {}

NOT_CHECKS = {'datadog_checks_dev', 'datadog_checks_tests_helper', 'ddev'}

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

CHECK_LINKS = """\
[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/kubernetes/integrations/
[4]: https://github.com/DataDog/{repository}/blob/master/{name}/datadog_checks/{name}/data/conf.yaml.example
[5]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[6]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[7]: https://github.com/DataDog/{repository}/blob/master/{name}/metadata.csv
[8]: https://github.com/DataDog/{repository}/blob/master/{name}/assets/service_checks.json
[9]: https://docs.datadoghq.com/help/
"""

LOGS_LINKS = """\
[1]: https://docs.datadoghq.com/help/
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[4]: **LINK_TO_INTEGRATION_SITE**
[5]: https://github.com/DataDog/{repository}/blob/master/{name}/assets/service_checks.json
"""

JMX_LINKS = """\
[1]: **LINK_TO_INTEGERATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://github.com/DataDog/{repository}/blob/master/{name}/datadog_checks/{name}/data/conf.yaml.example
[4]: https://docs.datadoghq.com/agent/guide/agent-commands/#agent-status-and-information
[5]: https://docs.datadoghq.com/integrations/java/
[6]: https://docs.datadoghq.com/help/
[7]: https://docs.datadoghq.com/agent/guide/agent-commands/#start-stop-and-restart-the-agent
[8]: https://github.com/DataDog/{repository}/blob/master/{name}/assets/service_checks.json
"""

SNMP_TILE_LINKS = """\
[1]: https://docs.datadoghq.com/network_performance_monitoring/devices/data
[2]: https://docs.datadoghq.com/network_performance_monitoring/devices/setup
[3]: https://github.com/DataDog/{repository}/blob/master/snmp_{name}/assets/service_checks.json
[4]: https://docs.datadoghq.com/help/
[5]: https://www.datadoghq.com/blog/monitor-snmp-with-datadog/
"""

TILE_LINKS = """\
[1]: **LINK_TO_INTEGRATION_SITE**
[2]: https://app.datadoghq.com/account/settings/agent/latest
[3]: https://docs.datadoghq.com/help/
"""

integration_type_links = {
    'check': CHECK_LINKS,
    'logs': LOGS_LINKS,
    'jmx': JMX_LINKS,
    'snmp_tile': SNMP_TILE_LINKS,
    'tile': TILE_LINKS,
    'metrics_crawler': TILE_LINKS,
}

# If a file changes in a PR with any of these file extensions,
# a test will run against the check containing the file
TESTABLE_FILE_PATTERNS = (
    '*.py',
    '*.ini',
    '*.in',
    '*.txt',
    '*.yml',
    '*.yaml',
    '**/tests/*',
    '**/pyproject.toml',
    '**/hatch.toml',
)
NON_TESTABLE_FILES = ('auto_conf.yaml', 'agent_requirements.in')

ROOT = ''

# Files searched for COPYRIGHT_RE
COPYRIGHT_LOCATIONS_RE = re.compile(r'^(license.*|notice.*|copying.*|copyright.*|readme.*)$', re.I)

# General match for anything that looks like a copyright declaration
COPYRIGHT_RE = re.compile(
    r'^(?!i\.e\.,.*$)(Copyright\s+(?:©|\(c\)\s+)?(?:(?:[0-9 ,-]|present)+\s+)?(?:by\s+)?(.*))$', re.I
)

# Copyright strings to ignore, as they are not owners.  Most of these are from
# boilerplate license files.
#
# These match at the beginning of the copyright (the result of COPYRIGHT_RE).
COPYRIGHT_IGNORE_RE = [
    re.compile(r'copyright(:? and license)?$', re.I),
    re.compile(r'copyright (:?holder|owner|notice|license|statement|law|on the Program|and Related)', re.I),
    re.compile(r'Copyright & License -'),
    re.compile(r'copyright .yyyy. .name of copyright owner.', re.I),
    re.compile(r'copyright \(c\) <year>\s{2}<name of author>', re.I),
    re.compile(r'.*\sFree Software Foundation', re.I),
]


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


def get_copyright_locations_re():
    return COPYRIGHT_LOCATIONS_RE


def get_copyright_re():
    return COPYRIGHT_RE


def get_copyright_ignore_re():
    return COPYRIGHT_IGNORE_RE
