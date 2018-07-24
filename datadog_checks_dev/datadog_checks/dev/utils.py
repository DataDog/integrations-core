# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform
import shutil
from contextlib import contextmanager
from io import open
from tempfile import mkdtemp

from six import PY3, text_type
from six.moves.urllib.request import urlopen

from .compat import FileNotFoundError, PermissionError

__platform = platform.system()
ON_MACOS = os.name == 'mac' or __platform == 'Darwin'
ON_WINDOWS = NEED_SHELL = os.name == 'nt' or __platform == 'Windows'


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


def dir_exists(d):
    return os.path.isdir(d)


def path_exists(p):
    return os.path.exists(p)


def ensure_dir_exists(d):
    if not dir_exists(d):
        os.makedirs(d)


def ensure_parent_dir_exists(path):
    ensure_dir_exists(os.path.dirname(os.path.abspath(path)))


def create_file(fname):
    ensure_parent_dir_exists(fname)
    with open(fname, 'a'):
        os.utime(fname, None)


def ensure_bytes(s):
    if not isinstance(s, bytes):
        s = s.encode('utf-8')
    return s


def ensure_unicode(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return s


def download_file(url, fname):
    req = urlopen(url)
    with open(fname, 'wb') as f:
        while True:
            chunk = req.read(16384)
            if not chunk:
                break
            f.write(chunk)
            f.flush()


def copy_path(path, d):
    if dir_exists(path):
        shutil.copytree(path, os.path.join(d, basepath(path)))
    else:
        shutil.copy(path, d)


def remove_path(path):
    try:
        shutil.rmtree(path, ignore_errors=True)
    except (FileNotFoundError, OSError):
        try:
            os.remove(path)
        except (FileNotFoundError, OSError, PermissionError):
            pass


def resolve_path(path, strict=False):
    path = os.path.expanduser(path or '')
    # TODO: On Python 3.6+ do `path = str(Path(path).resolve())`.
    path = os.path.realpath(path)

    return '' if strict and not os.path.exists(path) else path


def basepath(path):
    return os.path.basename(os.path.normpath(path))


def get_next(obj):
    return next(iter(obj))


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
def chdir(d, cwd=None):
    origin = cwd or os.getcwd()
    os.chdir(d)

    try:
        yield
    finally:
        os.chdir(origin)


@contextmanager
def temp_chdir(cwd=None):
    with temp_dir() as d:
        with chdir(d, cwd=cwd):
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


@contextmanager
def mock_context_manager(obj=None):
    yield obj
