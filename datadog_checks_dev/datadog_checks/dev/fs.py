# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Filesystem utility functions abstracting common operations, specially designed to be used
by Integrations within tests.
"""
import inspect
import os
import shutil
from contextlib import contextmanager
from io import open
from tempfile import mkdtemp

from six import PY3, text_type
from six.moves.urllib.request import urlopen

from .structures import EnvVars

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


def get_parent_dir(path):
    return os.path.dirname(os.path.abspath(path))


def get_here():
    return get_parent_dir(inspect.currentframe().f_back.f_code.co_filename)


def path_join(path, *paths):
    return os.path.join(path, *paths)


def write_file_binary(file, contents):
    with open(file, 'wb') as f:
        f.write(contents)


def read_file_binary(file):
    with open(file, 'rb') as f:
        return f.read()


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


def copy_dir_contents(path, d):
    for p in os.listdir(path):
        copy_path(os.path.join(path, p), d)


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


def resolve_path(path, strict=False):
    path = os.path.expanduser(path or '')
    # TODO: On Python 3.6+ do `path = str(Path(path).resolve())`.
    path = os.path.realpath(path)

    return '' if strict and not os.path.exists(path) else path


@contextmanager
def temp_dir():
    # TODO: On Python 3.5+ just use `with TemporaryDirectory() as d:`.
    d = mkdtemp()

    try:
        d = resolve_path(d)
        yield d
    finally:
        remove_path(d)


@contextmanager
def chdir(d, cwd=None, env_vars=None):
    origin = cwd or os.getcwd()
    os.chdir(d)
    if env_vars:
        env_vars = EnvVars(env_vars)
    else:
        from .utils import mock_context_manager

        env_vars = mock_context_manager()

    try:
        with env_vars:
            yield
    finally:
        os.chdir(origin)


@contextmanager
def temp_chdir(cwd=None, env_vars=None):
    with temp_dir() as d:
        with chdir(d, cwd=cwd, env_vars=env_vars):
            yield d


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
