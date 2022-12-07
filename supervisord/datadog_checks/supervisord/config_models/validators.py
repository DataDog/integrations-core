# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    # TODO: remove when deprecation is finalized https://github.com/DataDog/integrations-core/pull/9340
    if 'username' not in values and 'user' in values:
        values['username'] = values['user']
    if 'password' not in values and 'pass' in values:
        values['password'] = values['pass']

    return values
