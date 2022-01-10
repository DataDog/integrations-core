# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import itertools
import os
from glob import iglob
from os.path import join

from ..fs import dir_exists, remove_path
from .utils import is_package

DELETE_IN_ROOT = {'.cache', '.coverage', '.eggs', '.pytest_cache', '.tox', 'build', 'dist', '*.egg-info', '.benchmarks'}
DELETE_EVERYWHERE = {'__pycache__', '*.pyc', '*.pyd', '*.pyo', '*.whl'}
ALL_PATTERNS = DELETE_IN_ROOT | DELETE_EVERYWHERE


def remove_compiled_scripts(d, detect_project=True):
    removed = set()

    for root, _, files in generate_walker(d, detect_project):
        for file in files:
            if file.endswith('.pyc'):
                removed.add(join(root, file))

    removed = sorted(removed)

    for p in reversed(removed):
        remove_path(p)

    return removed


def find_globs(walker, patterns, matches):
    for root, dirs, files in walker:
        for d in dirs:
            d = join(root, d)
            for pattern in patterns:
                for p in iglob(join(d, pattern)):
                    matches.add(p)

        sub_files = set()
        for p in matches:
            if root.startswith(p):
                for f in files:
                    sub_files.add(join(root, f))

        matches.update(sub_files)


def clean_package(d, detect_project=True, force_clean_root=False):
    removed = set()
    patterns = ALL_PATTERNS.copy()

    removed_root_dirs = set()
    if detect_project:
        patterns.remove('*.egg-info')

    patterns_to_remove = DELETE_EVERYWHERE
    if force_clean_root:
        patterns_to_remove = ALL_PATTERNS

    for pattern in patterns:
        for path in iglob(join(d, pattern)):
            removed.add(path)
            if dir_exists(path):
                removed_root_dirs.add(path)
                find_globs(os.walk(path), DELETE_EVERYWHERE, removed)

    find_globs(generate_walker(d, detect_project, removed_root_dirs), patterns_to_remove, removed)

    removed = sorted(removed)

    for p in reversed(removed):
        remove_path(p)

    return removed


def generate_walker(d, detect_project=True, removed_root_dirs=None):
    walker = os.walk(d)
    r, dirs, f = next(walker)

    removed_root_dirs = removed_root_dirs or set()
    if detect_project and is_package(d):
        removed_root_dirs.add('venv')

    for root_dir in removed_root_dirs:
        try:
            dirs.remove(root_dir)
        except ValueError:
            pass

    return itertools.chain(((r, dirs, f),), walker)
