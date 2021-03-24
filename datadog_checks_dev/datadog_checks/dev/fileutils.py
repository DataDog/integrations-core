# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os
import shutil
from urllib.request import urlopen

from six import PY3, text_type


if PY3:

    def write_file(file, contents, encoding='utf-8'):
        with open(file, 'w', encoding=encoding) as f:
            f.write(contents)

    def write_file_lines(file, lines, encoding='utf-8'):
        with open(file, 'w', encoding=encoding) as f:
            f.writelines(lines)


else:

    def write_file(file, contents, encoding='utf-8'):
        with open(file, 'w', encoding=encoding) as f:
            f.write(text_type(contents))

    def write_file_lines(file, lines, encoding='utf-8'):
        with open(file, 'w', encoding=encoding) as f:
            f.writelines(text_type(line) for line in lines)


def dir_exists(d):
    return os.path.isdir(d)


def path_join(path, *paths):
    return os.path.join(path, *paths)


def write_file_binary(file, contents):
    with open(file, 'wb') as f:
        f.write(contents)


def read_file(file, encoding='utf-8'):
    with open(file, 'r', encoding=encoding) as f:
        return f.read()


def read_file_lines(file, encoding='utf-8'):
    with open(file, 'r', encoding=encoding) as f:
        return f.readlines()


def stream_file_lines(file, encoding='utf-8'):
    if file_exists(file):
        with open(file, 'r', encoding=encoding) as f:
            for line in f:
                yield line


def file_exists(f):
    return os.path.isfile(f)


def path_exists(p):
    return os.path.exists(p)


def resolve_dir_contents(d):
    for p in os.listdir(d):
        yield path_join(d, p)


def ensure_dir_exists(d):
    if not dir_exists(d):
        os.makedirs(d)


def get_parent_dir(path):
    return os.path.dirname(os.path.abspath(path))


def ensure_parent_dir_exists(path):
    ensure_dir_exists(get_parent_dir(path))


def create_file(fname):
    ensure_parent_dir_exists(fname)
    with open(fname, 'a'):
        os.utime(fname, None)


def download_file(url, fname):
    req = urlopen(url)
    with open(fname, 'wb') as f:
        while True:
            chunk = req.read(16384)
            if not chunk:
                break
            f.write(chunk)
            f.flush()


def basepath(path):
    return os.path.basename(os.path.normpath(path))


def copy_path(path, d):
    if dir_exists(path):
        return shutil.copytree(path, os.path.join(d, basepath(path)))
    else:
        return shutil.copy(path, d)


def remove_path(path):
    try:
        shutil.rmtree(path, ignore_errors=False)
    # TODO: Remove FileNotFoundError (and noqa: B014) when Python 2 is removed
    # In Python 3, IOError have been merged into OSError
    except (FileNotFoundError, OSError):  # noqa: B014
        try:
            os.remove(path)
        # TODO: Remove FileNotFoundError (and noqa: B014) when Python 2 is removed
        # In Python 3, IOError have been merged into OSError
        except (FileNotFoundError, OSError, PermissionError):  # noqa: B014
            pass


def read_file_binary(file):
    with open(file, 'rb') as f:
        return f.read()
