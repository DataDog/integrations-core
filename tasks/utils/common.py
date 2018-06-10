# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import json
import os
import re

from ..constants import ROOT

VERSION = re.compile(r'__version__ *= *(?:\'|")(.+?)(?:\'|")')
REVISION_DELIMITER = '-rev.'


def get_version_file(check_name):
    if check_name in ('datadog_checks_base', 'datadog_checks_test_helper'):
        return os.path.join(ROOT, check_name, "datadog_checks", "__about__.py")
    else:
        return os.path.join(ROOT, check_name, "datadog_checks", check_name, "__about__.py")


def read_version_file(check_name):
    with open(get_version_file(check_name), 'r') as f:
        return f.read()


def get_valid_checks():
    return {path for path in os.listdir(ROOT) if os.path.isfile(get_version_file(path))}


def get_version_string(check_name, release=True):
    """
    Get the version string for the given check.
    """
    version = VERSION.search(read_version_file(check_name))
    if version:
        version = version.group(1)
        return parse_release_version(version) if release else version


def parse_release_version(version):
    return version.split(REVISION_DELIMITER)[0]


def make_dev_version(version, rev):
    return '{}{}{}'.format(version, REVISION_DELIMITER, rev)


def get_release_tag_string(check_name, version_string):
    """
    Compose a string to use for release tags
    """
    return '{}-{}'.format(check_name, version_string)


def load_manifest(check_name):
    """
    Load the manifest file into a dictionary
    """
    manifest_path = os.path.join(ROOT, check_name, 'manifest.json')
    if os.path.exists(manifest_path):
        with open(manifest_path) as f:
            return json.load(f)
    return {}


def update_version_module(check_name, old_ver, new_ver):
    """
    Change the Python code in the __about__.py module so that `__version__`
    contains the new value.
    """
    contents = read_version_file(check_name)
    contents = contents.replace(old_ver, new_ver)
    with open(about_module, 'w') as f:
        f.write(contents)
