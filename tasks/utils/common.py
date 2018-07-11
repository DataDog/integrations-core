# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import json
import os
from contextlib import contextmanager

from ..constants import ROOT


@contextmanager
def chdir(d, cwd=None):
    origin = cwd or os.getcwd()
    os.chdir(d)

    try:
        yield
    finally:
        os.chdir(origin)


def get_version_file(check_name):
    if check_name in ('datadog_checks_base', 'datadog_checks_test_helper'):
        return os.path.join(ROOT, check_name, "datadog_checks", "__about__.py")
    else:
        return os.path.join(ROOT, check_name, "datadog_checks", check_name, "__about__.py")


def get_tox_file(check_name):
    return os.path.join(ROOT, check_name, 'tox.ini')


def get_valid_checks():
    return [path for path in os.listdir(ROOT) if os.path.isfile(get_version_file(path))]


def get_testable_checks():
    return [path for path in os.listdir(ROOT) if os.path.isfile(get_tox_file(path))]


def get_version_string(check_name):
    """
    Get the version string for the given check.
    """
    about = {}
    with open(get_version_file(check_name)) as f:
        exec(f.read(), about)

    return about.get('__version__')


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
    about_module = get_version_file(check_name)
    with open(about_module, 'r') as f:
        contents = f.read()

    contents = contents.replace(old_ver, new_ver)
    with open(about_module, 'w') as f:
        f.write(contents)
