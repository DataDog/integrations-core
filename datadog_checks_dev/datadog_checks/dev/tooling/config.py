# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import OrderedDict, deque
from copy import deepcopy

import toml
from appdirs import user_data_dir
from atomicwrites import atomic_write
from six import string_types

from ..compat import FileNotFoundError
from ..utils import ensure_parent_dir_exists, file_exists, read_file

APP_DIR = user_data_dir('dd-checks-dev', '')
CONFIG_FILE = os.path.join(APP_DIR, 'config.toml')

SECRET_KEYS = {
    'github.token',
    'pypi.pass',
    'trello.key',
    'trello.token',
}

DEFAULT_CONFIG = OrderedDict([
    ('core', os.path.join('~', 'dd', 'integrations-core')),
    ('extras', os.path.join('~', 'dd', 'integrations-extras')),
    ('github', OrderedDict((
        ('user', ''),
        ('token', ''),
    ))),
    ('pypi', OrderedDict((
        ('user', ''),
        ('pass', ''),
    ))),
    ('trello', OrderedDict((
        ('key', ''),
        ('token', ''),
    ))),
])


def config_file_exists():
    return file_exists(CONFIG_FILE)


def copy_default_config():
    return deepcopy(DEFAULT_CONFIG)


def save_config(config):
    ensure_parent_dir_exists(CONFIG_FILE)
    with atomic_write(CONFIG_FILE, mode='wb', overwrite=True) as f:
        f.write(toml.dumps(config).encode('utf-8'))


def load_config():
    config = copy_default_config()

    try:
        config.update(toml.loads(read_config_file(), OrderedDict))
    except FileNotFoundError:
        pass

    return config


def read_config_file():
    return read_file(CONFIG_FILE)


def read_config_file_scrubbed():
    return toml.dumps(scrub_secrets(load_config()))


def restore_config():
    config = copy_default_config()
    save_config(config)
    return config


def update_config():
    config = copy_default_config()
    config.update(load_config())
    save_config(config)
    return config


def scrub_secrets(config):
    for secret_key in SECRET_KEYS:
        branch = config
        paths = deque(secret_key.split('.'))

        while paths:
            path = paths.popleft()
            if not hasattr(branch, 'get'):
                break

            if path in branch:
                if not paths:
                    old_value = branch[path]
                    if isinstance(old_value, string_types):
                        branch[path] = '*' * len(old_value)
                else:
                    branch = branch[path]
            else:
                break

    return config
