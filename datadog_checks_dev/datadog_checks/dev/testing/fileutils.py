# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import inspect
import os
import shutil
from contextlib import contextmanager

from datadog_checks.dev.fileutils import copy_path, remove_path, get_parent_dir, file_exists, path_join


def copy_dir_contents(path, d):
    for p in os.listdir(path):
        copy_path(os.path.join(path, p), d)


def resolve_path(path, strict=False):
    path = os.path.expanduser(path or '')
    # TODO: On Python 3.6+ do `path = str(Path(path).resolve())`.
    path = os.path.realpath(path)

    return '' if strict and not os.path.exists(path) else path


@contextmanager
def temp_move_path(path, d):
    if os.path.exists(path):
        dst = shutil.move(path, d)

        try:
            yield dst
        finally:
            try:
                os.replace(dst, path)
            except OSError:  # no cov
                shutil.move(dst, path)
    else:
        try:
            yield
        finally:
            remove_path(path)


def find_check_root(depth=0):
    # Account for this call
    depth += 1

    frame = inspect.currentframe()
    for _ in range(depth):
        frame = frame.f_back

    root = get_parent_dir(frame.f_code.co_filename)
    while True:
        if file_exists(path_join(root, 'setup.py')):
            break

        new_root = os.path.dirname(root)
        if new_root == root:
            raise OSError('No check found')

        root = new_root

    return root
