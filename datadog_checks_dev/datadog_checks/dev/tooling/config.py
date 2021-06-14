# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from collections import deque
from copy import deepcopy

import toml
from atomicwrites import atomic_write
from platformdirs import user_data_dir

from ..fs import ensure_parent_dir_exists, file_exists, read_file

APP_DIR = user_data_dir('dd-checks-dev', '')
CONFIG_FILE = os.path.join(APP_DIR, 'config.toml')

SECRET_KEYS = {
    'dd_api_key',
    'dd_app_key',
    'orgs.*.api_key',
    'orgs.*.app_key',
    'github.token',
    'pypi.pass',
    'trello.key',
    'trello.token',
}

DEFAULT_CONFIG = {
    'repo': 'core',
    'agent': 'master',
    'org': 'default',
    'color': bool(int(os.environ['DDEV_COLOR'])) if 'DDEV_COLOR' in os.environ else None,
    'dd_api_key': os.getenv('DD_API_KEY'),
    'dd_app_key': os.getenv('DD_APP_KEY'),
    'github': {'user': '', 'token': ''},
    'pypi': {'user': '', 'pass': ''},
    'trello': {'key': '', 'token': ''},
    'repos': {
        'core': os.path.join('~', 'dd', 'integrations-core'),
        'extras': os.path.join('~', 'dd', 'integrations-extras'),
        'agent': os.path.join('~', 'dd', 'datadog-agent'),
        'marketplace': os.path.join('~', 'dd', 'marketplace'),
    },
    'agents': {
        'master': {'docker': 'datadog/agent-dev:master', 'local': 'latest'},
        '7': {'docker': 'datadog/agent:7', 'local': '7'},
        '6': {'docker': 'datadog/agent:6', 'local': '6'},
    },
    'orgs': {
        'default': {
            'api_key': os.getenv('DD_API_KEY'),
            'app_key': os.getenv('DD_APP_KEY'),
            'site': os.getenv('DD_SITE'),
            'dd_url': os.getenv('DD_DD_URL'),
            'log_url': os.getenv('DD_LOGS_CONFIG_DD_URL'),
        }
    },
}


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
        config.update(toml.loads(read_config_file()))
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
                    if isinstance(old_value, str):
                        branch[path] = '*' * len(old_value)
                else:
                    branch = branch[path]
            else:
                break

    for data in config.get('orgs', {}).values():
        api_key = data.get('api_key')
        if api_key:
            data['api_key'] = '*' * len(api_key)

        app_key = data.get('app_key')
        if app_key:
            data['app_key'] = '*' * len(app_key)

    return config
