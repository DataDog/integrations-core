# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.dev.env import deserialize_data, get_env_vars, serialize_data, set_env_vars


def get_client_token_path():
    return deserialize_data(get_env_vars().get('client_token_path'))


def set_client_token_path(client_token_path):
    set_env_vars({'client_token_path': serialize_data(client_token_path)})
