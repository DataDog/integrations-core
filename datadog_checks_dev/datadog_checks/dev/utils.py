# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Utilities functions abstracting common operations, specially designed to be used
by Integrations within tests.
"""
import csv
import inspect
import os
import platform
import shutil
import socket
from contextlib import closing, contextmanager
from io import open
from tempfile import mkdtemp

import yaml
from six import PY3, text_type
from six.moves.urllib.request import urlopen

from .compat import FileNotFoundError, PermissionError
from .structures import EnvVars

__platform = platform.system()
ON_MACOS = os.name == 'mac' or __platform == 'Darwin'
ON_WINDOWS = NEED_SHELL = os.name == 'nt' or __platform == 'Windows'
ON_LINUX = not (ON_MACOS or ON_WINDOWS)


def get_tox_env():
    return os.environ['TOX_ENV_NAME']


def get_ci_env_vars():
    return ('AGENT_OS', 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI')


def running_on_ci():
    return 'SYSTEM_TEAMFOUNDATIONCOLLECTIONURI' in os.environ


def running_on_windows_ci():
    return running_on_ci() and os.environ.get('AGENT_OS') == 'Windows_NT'


def running_on_linux_ci():
    return running_on_ci() and os.environ.get('AGENT_OS') == 'Linux'


def running_on_macos_ci():
    return running_on_ci() and os.environ.get('AGENT_OS') == 'Darwin'


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


def dir_exists(d):
    return os.path.isdir(d)


def path_exists(p):
    return os.path.exists(p)


def path_join(path, *paths):
    return os.path.join(path, *paths)


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


def basepath(path):
    return os.path.basename(os.path.normpath(path))


def get_next(obj):
    return next(iter(obj))


def get_here():
    return get_parent_dir(inspect.currentframe().f_back.f_code.co_filename)


def load_jmx_config():
    # Only called in tests of a check, so just go back one frame
    root = find_check_root(depth=1)

    check = basepath(root)
    example_config_path = path_join(root, 'datadog_checks', check, 'data', 'conf.yaml.example')
    metrics_config_path = path_join(root, 'datadog_checks', check, 'data', 'metrics.yaml')

    example_config = yaml.safe_load(read_file(example_config_path))
    metrics_config = yaml.safe_load(read_file(metrics_config_path))

    # Avoid having to potentially mount multiple files by putting the default metrics
    # in the user-defined metric location.
    example_config['init_config']['conf'] = metrics_config['jmx_metrics']

    return example_config


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


def get_current_check_name(depth=0):
    # Account for this call
    depth += 1

    return os.path.basename(find_check_root(depth))


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
    env_vars = EnvVars(env_vars) if env_vars else mock_context_manager()

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


@contextmanager
def mock_context_manager(obj=None):
    yield obj


def find_free_port(ip):
    """Return a port available for listening on the given `ip`."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((ip, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def get_ip():
    """Return the IP address used to connect to external networks."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]


def get_metadata_metrics():
    # Only called in tests of a check, so just go back one frame
    root = find_check_root(depth=1)
    metadata_path = os.path.join(root, 'metadata.csv')
    metrics = {}
    with open(metadata_path) as f:
        for row in csv.DictReader(f):
            metrics[row['metric_name']] = row
    return metrics
