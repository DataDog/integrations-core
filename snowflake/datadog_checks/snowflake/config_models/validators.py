# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    # TODO: remove when deprecation is finalized https://github.com/DataDog/integrations-core/pull/9340
    if 'username' not in values and 'user' in values:
        values['username'] = values['user']

    _validate_authenticator_option(values)

    if 'private_key_password' in values and 'private_key_path' not in values:
        raise Exception(
            'Option `private_key_password` is set but not option `private_key_path`. '
            'Set `private_key_path` or remove `private_key_password` entry.'
        )

    if values.get('only_custom_queries', False) and len(values('metric_groups', [])) > 0:
        raise Exception(
            'Option `only_custom_queries` and `metric_groups` are not compatible.'
            '`only_custom_queries` prevents `metric_groups` to be collected.'
        )

    return values


def _validate_authenticator_option(values):
    authenticator = values.get('authenticator', 'snowflake')
    # `key` needs at list one item in `values` to be set
    authenticator_dependencies = {
        'snowflake': ['password', 'private_key_path'],
        'snowflake_jwt': ['private_key_path'],
        'oauth': ['token', 'token_path'],
    }

    if authenticator not in authenticator_dependencies:
        raise Exception(
            'Unkwown authenticator option {}, supported options are {}.'.format(
                authenticator, authenticator_dependencies.keys()
            )
        )

    if not any([opt in values for opt in authenticator_dependencies[authenticator]]):
        raise Exception(
            'Authenticator option `{}` needs `{}` option to be set.'.format(
                authenticator, '` or `'.join(authenticator_dependencies[authenticator])
            )
        )
