# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals
import os

from .constants import ROOT


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


def get_current_branch(ctx):
    """
    Get the current branch name.
    """
    cmd = "git rev-parse --abbrev-ref HEAD"
    return ctx.run(cmd, hide='out').stdout


def get_release_tag_string(check_name, version_string):
    """
    Compose a string to use for release tags
    """
    return '{}-{}'.format(check_name, version_string)
