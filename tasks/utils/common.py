# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os
import json

from ..constants import ROOT


def get_version_string(check_name):
    """
    Get the version string for the given check.
    """
    about = {}
    if check_name in ('datadog_checks_base', 'datadog_checks_test_helper'):
        about_path = os.path.join(ROOT, check_name, "datadog_checks", "__about__.py")
    else:
        about_path = os.path.join(ROOT, check_name, "datadog_checks", check_name, "__about__.py")
    with open(about_path) as f:
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
    about_module = os.path.join(ROOT, check_name, 'datadog_checks', check_name, '__about__.py')
    with open(about_module, 'r') as f:
        contents = f.read()

    contents = contents.replace(old_ver, new_ver)
    with open(about_module, 'w') as f:
        f.write(contents)
