# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import unicode_literals

import re

from ..._env import E2E_FIXTURE_NAME, deserialize_data

CONFIG_MESSAGE_PATTERN = 'DDEV_E2E_START_MESSAGE (.+) DDEV_E2E_END_MESSAGE'


def parse_config_from_result(env, result):
    if 'NO E2E FIXTURE AVAILABLE' in result.stdout:
        return None, None, 'The environment fixture `{}` does not exist.'.format(E2E_FIXTURE_NAME)

    if '{}: platform mismatch'.format(env) in result.stdout:
        return None, None, 'The environment `{}` does not support this platform.'.format(env)

    decoded = parse_encoded_config_data(result.stdout)
    if decoded is None:
        return (
            None,
            None,
            (
                '{}\n{}\nUnable to parse configuration. Try recreating your env to get the '
                'latest version of the dev package.'.format(result.stdout, result.stderr)
            ),
        )

    config = decoded['config']
    metadata = decoded['metadata']

    if config is None:
        return None, None, 'The environment fixture `{}` did not yield any configuration.'.format(E2E_FIXTURE_NAME)

    return config, metadata, None


def parse_encoded_config_data(output):
    match = re.search(CONFIG_MESSAGE_PATTERN, output)
    if match:
        return deserialize_data(match.group(1))
