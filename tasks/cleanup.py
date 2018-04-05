# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import os
import fnmatch
import shutil

from invoke import task

from .constants import ROOT


@task(help={})
def cleanup(ctx):
    """
    Cleanup all temporary files and directories

    Example invocation:
        inv cleanup
    """
    should_delete_directories = [
        ".eggs",
        ".pytest_cache",
        ".tox",
        "__pycache__"
    ]

    should_delete_directories_globs = [
        "*.egg-info"
    ]

    for path, dirnames, filenames in os.walk('.'):
        for filename in fnmatch.filter(filenames, '*.pyc'):
            file_path = os.path.join(ROOT, path, filename)
            os.remove(file_path)

        for dirname in dirnames:
            if dirname in should_delete_directories:
                dir_path = os.path.join(ROOT, path, dirname)
                shutil.rmtree(dir_path)

        for dir_glob in should_delete_directories_globs:
            for dirname in fnmatch.filter(dirnames, dir_glob):
                dir_path = os.path.join(ROOT, path, dirname)
                shutil.rmtree(dir_path)
