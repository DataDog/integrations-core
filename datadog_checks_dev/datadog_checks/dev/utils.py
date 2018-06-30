# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import platform
import shlex
import shutil
from collections import namedtuple
from contextlib import contextmanager
from io import open
from subprocess import Popen
from tempfile import TemporaryFile, mkdtemp

from six import PY3, text_type
from six.moves.urllib.request import urlopen

from .errors import SubprocessError

__platform = platform.system()
ON_MACOS = os.name == 'mac' or __platform == 'Darwin'
ON_WINDOWS = NEED_SHELL = os.name == 'nt' or __platform == 'Windows'

SubprocessResult = namedtuple('SubprocessResult', ('stdout', 'stderr', 'code'))


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


def run_command(command, capture=None, check=False, encoding='utf-8', shell=False, env=None):
    if shell == 'detect':
        shell = NEED_SHELL

    if isinstance(command, str) and not ON_WINDOWS:
        command = shlex.split(command)

    if capture:
        if capture is True or capture == 'both':
            stdout, stderr = TemporaryFile, TemporaryFile
        elif capture in ('stdout', 'out'):
            stdout, stderr = TemporaryFile, mock_context_manager
        elif capture in ('stderr', 'err'):
            stdout, stderr = mock_context_manager, TemporaryFile
        else:
            raise ValueError('Unknown capture method `{}`'.format(capture))
    else:
        stdout, stderr = mock_context_manager, mock_context_manager

    with stdout() as stdout, stderr() as stderr:
        process = Popen(command, stdout=stdout, stderr=stderr, shell=shell, env=env)
        process.wait()

        if stdout is None:
            stdout = ''
        else:
            stdout.seek(0)
            stdout = stdout.read().decode(encoding)

        if stderr is None:
            stderr = ''
        else:
            stderr.seek(0)
            stderr = stderr.read().decode(encoding)

    if check and process.returncode != 0:
        raise SubprocessError(
            'Command: {}\n'
            'Exit code: {}\n'
            'Captured Output: {}'.format(
                command,
                process.returncode,
                stdout + stderr
            )
        )

    return SubprocessResult(stdout, stderr, process.returncode)


def file_exists(f):
    return os.path.isfile(f)


def dir_exists(d):
    return os.path.isdir(d)


def ensure_dir_exists(d):
    if not dir_exists(d):
        os.makedirs(d)


def ensure_parent_dir_exists(path):
    ensure_dir_exists(os.path.dirname(os.path.abspath(path)))


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


def copy_path(path, d):
    if dir_exists(path):
        shutil.copytree(path, os.path.join(d, basepath(path)))
    else:
        shutil.copy(path, d)


def remove_path(path):
    try:
        shutil.rmtree(path)
    except (FileNotFoundError, OSError):
        try:
            os.remove(path)
        except (FileNotFoundError, PermissionError):
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
def chdir(d, cwd=None):
    origin = cwd or os.getcwd()
    os.chdir(d)

    try:
        yield
    finally:
        os.chdir(origin)


@contextmanager
def temp_chdir(cwd=None):
    origin = cwd or os.getcwd()

    # TODO: On Python 3.5+ wrap everything with `with TemporaryDirectory() as d:`.
    d = mkdtemp()
    os.chdir(d)

    try:
        yield resolve_path(d)
    finally:
        os.chdir(origin)


@contextmanager
def env_vars(evars, ignore=None):
    ignore = ignore or {}
    ignored_evars = {}
    old_evars = {}

    for ev in evars:
        if ev in os.environ:
            old_evars[ev] = os.environ[ev]
        os.environ[ev] = evars[ev]

    for ev in ignore:
        if ev in os.environ:  # no cov
            ignored_evars[ev] = os.environ[ev]
            os.environ.pop(ev)

    try:
        yield
    finally:
        for ev in evars:
            if ev in old_evars:
                os.environ[ev] = old_evars[ev]
            else:
                os.environ.pop(ev)

        for ev in ignored_evars:
            os.environ[ev] = ignored_evars[ev]


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
