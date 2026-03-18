# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Environment data serialization utilities and constants ported from datadog_checks_dev._env.
"""
import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode

DDTRACE_OPTIONS_LIST = [
    'DD_TAGS',
    'DD_TRACE*',
    'DD_PROFILING*',
    'DD_SERVICE',
    'DD_AGENT_HOST',
    'DD_ENV',
]
E2E_PREFIX = 'DDEV_E2E'
E2E_ENV_VAR_PREFIX = f'{E2E_PREFIX}_ENV_'
E2E_SET_UP = f'{E2E_PREFIX}_UP'
E2E_TEAR_DOWN = f'{E2E_PREFIX}_DOWN'
E2E_PARENT_PYTHON = f'{E2E_PREFIX}_PARENT_PYTHON'
E2E_RESULT_FILE = f'{E2E_PREFIX}_RESULT_FILE'

E2E_FIXTURE_NAME = 'dd_environment'
TESTING_PLUGIN = 'DDEV_TESTING_PLUGIN'
SKIP_ENVIRONMENT = 'DDEV_SKIP_ENV'


def serialize_data(data):
    data = json.dumps(data, separators=(',', ':'))
    return urlsafe_b64encode(data.encode('utf-8')).decode('utf-8')


def deserialize_data(data):
    decoded = urlsafe_b64decode(data.encode('utf-8'))
    return json.loads(decoded.decode('utf-8'))


def format_config(config):
    if 'instances' not in config:
        config = {'instances': [config]}

    if 'init_config' not in config:
        config = dict(init_config={}, **config)

    return config


def e2e_active():
    return (
        E2E_SET_UP in os.environ
        or E2E_TEAR_DOWN in os.environ
        or E2E_PARENT_PYTHON in os.environ
        or any(ev.startswith(E2E_ENV_VAR_PREFIX) for ev in os.environ)
    )


def set_up_env():
    return os.getenv(E2E_SET_UP, 'true') != 'false'


def tear_down_env():
    return os.getenv(E2E_TEAR_DOWN, 'true') != 'false'


def get_env_vars():
    return {
        key[len(E2E_ENV_VAR_PREFIX):]: value
        for key, value in os.environ.items()
        if key.startswith(E2E_ENV_VAR_PREFIX)
    }


def set_env_vars(env_vars):
    for key, value in env_vars.items():
        os.environ[f'{E2E_ENV_VAR_PREFIX}{key}'] = value


def remove_env_vars(keys):
    for key in keys:
        os.environ.pop(f'{E2E_ENV_VAR_PREFIX}{key}', None)


def get_state(key, default=None):
    value = get_env_vars().get(key.lower())
    if value is None:
        return default
    return deserialize_data(value)


def save_state(key, value):
    set_env_vars({key.lower(): serialize_data(value)})
