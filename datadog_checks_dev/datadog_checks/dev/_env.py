# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from base64 import urlsafe_b64decode, urlsafe_b64encode

from six import iteritems

E2E_PREFIX = 'DDEV_E2E'
E2E_ENV_VAR_PREFIX = '{}_ENV_'.format(E2E_PREFIX)
E2E_SET_UP = '{}_UP'.format(E2E_PREFIX)
E2E_TEAR_DOWN = '{}_DOWN'.format(E2E_PREFIX)
E2E_PARENT_PYTHON = '{}_PYTHON_PATH'.format(E2E_PREFIX)
AGENT_COLLECTOR_SEPARATOR = '=== JSON ==='

E2E_FIXTURE_NAME = 'dd_environment'
TESTING_PLUGIN = 'DDEV_TESTING_PLUGIN'
SKIP_ENVIRONMENT = 'DDEV_SKIP_ENV'


def e2e_active():
    return any(ev.startswith(E2E_PREFIX) for ev in os.environ)


def e2e_testing():
    return E2E_PARENT_PYTHON in os.environ


def set_env_vars(env_vars):
    for key, value in iteritems(env_vars):
        key = '{}{}'.format(E2E_ENV_VAR_PREFIX, key)
        os.environ[key] = value


def remove_env_vars(env_vars):
    for ev in env_vars:
        os.environ.pop('{}{}'.format(E2E_ENV_VAR_PREFIX, ev), None)


def get_env_vars(raw=False):
    if raw:
        return {key: value for key, value in iteritems(os.environ) if key.startswith(E2E_ENV_VAR_PREFIX)}
    else:
        env_vars = {}

        for key, value in iteritems(os.environ):
            _, found, ev = key.partition(E2E_ENV_VAR_PREFIX)
            if found:
                # Normalize casing for Windows
                env_vars[ev.lower()] = value

        return env_vars


def get_state(key, default=None):
    value = get_env_vars().get(key.lower())
    if value is None:
        return default

    return deserialize_data(value)


def save_state(key, value):
    set_env_vars({key.lower(): serialize_data(value)})


def set_up_env():
    return os.getenv(E2E_SET_UP, 'true') != 'false'


def tear_down_env():
    return os.getenv(E2E_TEAR_DOWN, 'true') != 'false'


def format_config(config):
    if 'instances' not in config:
        config = {'instances': [config]}

    # Agent 5 requires init_config
    if 'init_config' not in config:
        config = dict(init_config={}, **config)

    return config


def replay_check_run(agent_collector, stub_aggregator):
    errors = []
    for collector in agent_collector:
        aggregator = collector['aggregator']
        runner = collector.get('runner', {})
        check_id = runner.get('CheckID', '')
        check_name = runner.get('CheckName', '')

        for data in aggregator.get('metrics', []):
            for _, value in data['points']:
                metric_type = stub_aggregator.METRIC_ENUM_MAP[data['type']]
                stub_aggregator.submit_metric_e2e(
                    # device is only present when replaying e2e tests. In integration tests it will be a tag
                    check_name,
                    check_id,
                    metric_type,
                    data['metric'],
                    value,
                    data['tags'],
                    data['host'],
                    data.get('device'),
                )

        for data in aggregator.get('service_checks', []):
            stub_aggregator.submit_service_check(
                check_name, check_id, data['check'], data['status'], data['tags'], data['host_name'], data['message']
            )

        if runner.get('LastError'):
            errors.extend(json.loads(runner['LastError']))
    if errors:
        raise Exception("\n".join("Message: {}\n{}".format(err['message'], err['traceback']) for err in errors))


def serialize_data(data):
    data = json.dumps(data, separators=(',', ':'))
    # Using base64 ensures:
    # 1. Printing to stdout won't fail
    # 2. Easy parsing since there are no spaces
    #
    # TODO: Remove str() when we drop Python 2
    return str(urlsafe_b64encode(data.encode('utf-8')).decode('utf-8'))


def deserialize_data(data):
    decoded = urlsafe_b64decode(data.encode('utf-8'))
    return json.loads(decoded.decode('utf-8'))
