# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import print_function, unicode_literals

import os
import fnmatch
import shutil

from invoke import task

from .constants import ROOT


@task(help={
    'dry-run': 'Print out files and directories that will be deleted without deleting them'
})
def cleanup(ctx, dry_run=False):
    """
    Cleanup all temporary files and directories

    Example invocation:
        inv cleanup
    """
    should_delete_directories = [
        ".eggs",
        ".pytest_cache",
        ".tox",
        "__pycache__",
        "build"
    ]

    should_delete_directories_globs = [
        "*.egg-info"
    ]

    should_delete_file_globs = [
        "*.whl",
        '*.pyc'
    ]

    for path, dirnames, filenames in os.walk('.'):
        for file_glob in should_delete_file_globs:
            for filename in fnmatch.filter(filenames, file_glob):
                file_path = os.path.join(ROOT, path, filename)
                if not dry_run:
                    os.remove(file_path)
                else:
                    print(file_path)

        for dirname in dirnames:
            if dirname in should_delete_directories:
                dir_path = os.path.join(ROOT, path, dirname)
                if not dry_run:
                    shutil.rmtree(dir_path)
                else:
                    print(dir_path)

        for dir_glob in should_delete_directories_globs:
            for dirname in fnmatch.filter(dirnames, dir_glob):
                dir_path = os.path.join(ROOT, path, dirname)
                if not dry_run:
                    shutil.rmtree(dir_path)
                else:
                    print(dir_path)
