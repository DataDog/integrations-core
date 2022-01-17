# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
AUTHENTICATOR_NEEDS = {
    'snowflake': [],
    'snowflake_jwt': ['private_key_path'],
    'oauth': ['token'],
}


def initialize_instance(values, **kwargs):
    # TODO: remove when deprecation is finalized https://github.com/DataDog/integrations-core/pull/9340
    if 'username' not in values and 'user' in values:
        values['username'] = values['user']

    return _validate_authenticator(values)


def _validate_authenticator(values):
    authenticator = values.get('authenticator', 'snowflake')

    if not AUTHENTICATOR_NEEDS.get(authenticator):
        raise ValueError(
            'Authenticator method `{}` is not valid. Supported methods are {}. " \
            "Please update Snowflake integration configuration to use a supported method.'.format(
                authenticator, AUTHENTICATOR_NEEDS.keys()
            )
        )

    missing_value_error = []
    for option in AUTHENTICATOR_NEEDS[authenticator]:
        if not values.get(option):
            missing_value_error.append(option)

    if len(missing_value_error) > 0:
        raise ValueError(
            '{} configuration option(s) are missing to use `{}` authenticator method. " \
                "Please set these options in the Snowflake integration configuration.'.format(
                ', '.join(missing_value_error), authenticator
            )
        )

    return values
