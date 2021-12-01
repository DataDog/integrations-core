# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Utilities functions abstracting common operations, specially designed to be used
by Integrations within tests.
"""
import os
import platform
import socket
from contextlib import closing, contextmanager

from .check_utils import get_metadata_metrics as cu_get_metadata_metrics
from .ci import running_on_ci, running_on_gh_actions, running_on_windows_ci  # noqa: F401

__platform = platform.system()
ON_MACOS = os.name == 'mac' or __platform == 'Darwin'
ON_WINDOWS = NEED_SHELL = os.name == 'nt' or __platform == 'Windows'
ON_LINUX = not (ON_MACOS or ON_WINDOWS)
GH_ANNOTATION_LEVELS = ['warning', 'error']


def get_tox_env():
    return os.environ['TOX_ENV_NAME']


def ensure_bytes(s):
    if not isinstance(s, bytes):
        s = s.encode('utf-8')
    return s


def ensure_unicode(s):
    if isinstance(s, bytes):
        s = s.decode('utf-8')
    return s


def get_next(obj):
    return next(iter(obj))


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


# Left for retrocompatibility
def get_metadata_metrics():
    return cu_get_metadata_metrics()
