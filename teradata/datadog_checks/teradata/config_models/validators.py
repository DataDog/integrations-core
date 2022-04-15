# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError

CREDENTIALS_OPTIONAL = ['JWT', 'KRB5', 'LDAP', 'TDNEGO']
VALID_SSL_MODES = ['ALLOW', 'DISABLE', 'PREFER', 'REQUIRE']
VALID_AUTH_MECHS = ['TD2', 'TDNEGO', 'LDAP', 'KRB5', 'JWT']
AUTH_DATA_REQUIRED = ['JWT', 'KRB5', 'LDAP']


def initialize_instance(values, **kwargs):
    if values.get('auth_mechanism') and values.get('auth_mechanism').upper() not in CREDENTIALS_OPTIONAL:
        if not values.get('username') or not values.get('password'):
            raise ConfigurationError('`username` and `password` are required.')

    if values.get('auth_mechanism') and values.get('auth_mechanism').upper() not in VALID_AUTH_MECHS:
        raise ConfigurationError(
            'Specified `auth_mechanism`: {} is not a valid option. Specify one of "TD2",'
            '"TDNEGO", "LDAP", "KRB5" or "JWT". '
            'Refer to the Datadog documentation for more information.'.format(values.get('auth_mechanism'))
        )

    if values.get('ssl_mode') and values.get('ssl_mode').upper() not in VALID_SSL_MODES:
        raise ConfigurationError(
            'Specified `ssl_mode`: {} is not a valid option. Specify one of "ALLOW", "DISABLE",'
            '"PREFER", or "REQUIRE". Refer to the Datadog documentation for more information.'.format(
                values.get('ssl_mode')
            )
        )
    if (
        not values.get('auth_data')
        and values.get('auth_mechanism')
        and values.get('auth_mechanism').upper() in AUTH_DATA_REQUIRED
    ):
        raise ConfigurationError('`auth_data` is required for auth_mechanism: {}.'.format(values.get('auth_mechanism')))

    return values
