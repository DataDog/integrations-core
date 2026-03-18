# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Legacy utility functions ported from datadog_checks_dev.
Only the functions actually used by the tooling layer are included here.
"""

import os
import platform
import socket
from contextlib import closing, contextmanager
from urllib.request import urlopen

# Re-export commonly used fs functions that were accessible via datadog_checks.dev.utils
from ddev.utils._compat_fs import (
    basepath,
    file_exists,
    get_parent_dir,
    path_join,
    read_file,
)

__platform = platform.system()
ON_MACOS = os.name == 'mac' or __platform == 'Darwin'
ON_WINDOWS = NEED_SHELL = os.name == 'nt' or __platform == 'Windows'
ON_LINUX = not (ON_MACOS or ON_WINDOWS)
GH_ANNOTATION_LEVELS = ['warning', 'error']


@contextmanager
def mock_context_manager(obj=None):
    yield obj


def get_hostname():
    """Return the socket hostname."""
    return socket.gethostname()


def find_free_port(ip: str) -> int:
    """Return a port available for listening on the given `ip`."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind((ip, 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def get_ip():
    """Return the IP address used to connect to external networks."""
    with closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
        s.connect(('10.255.255.255', 1))
        return s.getsockname()[0]


def get_next(obj):
    return next(iter(obj))


def download_file(url, fname):
    req = urlopen(url)
    with open(fname, 'wb') as f:
        while True:
            chunk = req.read(16384)
            if not chunk:
                break
            f.write(chunk)
            f.flush()
