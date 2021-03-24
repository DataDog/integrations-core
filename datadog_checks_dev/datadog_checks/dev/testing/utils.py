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
import socket
from contextlib import closing, contextmanager
from fnmatch import fnmatch
from io import open

import yaml
from datadog_checks.dev.fileutils import get_parent_dir, read_file, basepath, path_join
from datadog_checks.dev.testing.constants import NON_TESTABLE_FILES, TESTABLE_FILE_PATTERNS
from datadog_checks.dev.testing.fileutils import find_check_root
from datadog_checks.dev.tooling.git import files_changed

__platform = platform.system()
ON_MACOS = os.name == 'mac' or __platform == 'Darwin'
ON_WINDOWS = NEED_SHELL = os.name == 'nt' or __platform == 'Windows'
ON_LINUX = not (ON_MACOS or ON_WINDOWS)


def format_config(config):
    if 'instances' not in config:
        config = {'instances': [config]}

    # Agent 5 requires init_config
    if 'init_config' not in config:
        config = dict(init_config={}, **config)

    return config


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


def get_current_check_name(depth=0):
    # Account for this call
    depth += 1

    return os.path.basename(find_check_root(depth))


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


def testable_files(files):
    """
    Given a list of files, return only those that match any of the TESTABLE_FILE_PATTERNS and are
    not blacklisted by NON_TESTABLE_FILES (metrics.yaml, auto_conf.yaml)
    """
    filtered = []

    for f in files:
        if f.endswith(NON_TESTABLE_FILES):
            continue

        match = any(fnmatch(f, pattern) for pattern in TESTABLE_FILE_PATTERNS)
        if match:
            filtered.append(f)

    return filtered


def get_changed_checks():
    # Get files that changed compared to `master`
    changed_files = files_changed()

    # Filter by files that can influence the testing of a check
    changed_files[:] = testable_files(changed_files)

    return {line.split('/')[0] for line in changed_files}