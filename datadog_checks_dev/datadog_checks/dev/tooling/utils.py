# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
import re
from ast import literal_eval

import requests

from .constants import get_root
from ..utils import file_exists, read_file

# match something like `(#1234)` and return `1234` in a group
PR_PATTERN = re.compile(r'\(#(\d+)\)')

VERSION = re.compile(r'__version__ *= *(?:[\'"])(.+?)(?:[\'"])')


def format_commit_id(commit_id):
    if commit_id:
        if commit_id.isdigit():
            return 'PR #{}'.format(commit_id)
        else:
            return 'commit hash `{}`'.format(commit_id)
    return commit_id


def parse_pr_number(log_line):
    match = re.search(PR_PATTERN, log_line)
    if match:
        return match.group(1)


def get_current_agent_version():
    release_data = requests.get(
        'https://raw.githubusercontent.com/DataDog/datadog-agent/master/release.json'
    ).json()
    versions = set()

    for version in release_data:
        parts = version.split('.')
        if len(parts) > 1:
            versions.add((parts[0], parts[1]))

    return '.'.join(sorted(versions)[-1][:2])


def is_package(d):
    return file_exists(os.path.join(d, 'setup.py'))


def normalize_package_name(package_name):
    return re.sub(r'[-_. ]+', '_', package_name).lower()


def string_to_toml_type(s):
    if s.isdigit():
        s = int(s)
    elif s == 'true':
        s = True
    elif s == 'false':
        s = False
    elif s.startswith('['):
        s = literal_eval(s)

    return s


def get_version_file(check_name):
    if check_name in ('datadog_checks_base', 'datadog_checks_test_helper'):
        return os.path.join(get_root(), check_name, 'datadog_checks', '__about__.py')
    elif check_name == 'datadog_checks_dev':
        return os.path.join(get_root(), check_name, 'datadog_checks', 'dev', '__about__.py')
    else:
        return os.path.join(get_root(), check_name, 'datadog_checks', check_name, '__about__.py')


def get_tox_file(check_name):
    return os.path.join(get_root(), check_name, 'tox.ini')


def get_valid_checks():
    return {path for path in os.listdir(get_root()) if file_exists(get_version_file(path))}


def get_testable_checks():
    return {path for path in os.listdir(get_root()) if file_exists(get_tox_file(path))}


def read_version_file(check_name):
    return read_file(get_version_file(check_name))


def get_version_string(check_name):
    """
    Get the version string for the given check.
    """
    version = VERSION.search(read_version_file(check_name))
    if version:
        return version.group(1)


def load_manifest(check_name):
    """
    Load the manifest file into a dictionary
    """
    manifest_path = os.path.join(get_root(), check_name, 'manifest.json')
    if file_exists(manifest_path):
        return json.loads(read_file(manifest_path))
    return {}
