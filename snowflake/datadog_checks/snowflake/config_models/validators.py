# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    # TODO: remove when deprecation is finalized https://github.com/DataDog/integrations-core/pull/9340
    if 'username' not in values and 'user' in values:
        values['username'] = values['user']

    if 'private_key_password' in values and 'private_key_path' not in values:
        raise Exception(
            'Option `private_key_password` is set but not option `private_key_path`. '
            'Set `private_key_path` or remove `private_key_password` entry.'
        )

    return values
