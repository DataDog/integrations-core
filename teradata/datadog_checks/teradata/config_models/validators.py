# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
CREDENTIALS_OPTIONAL = ['JWT', 'KRB5', 'LDAP', 'TDNEGO']
VALID_SSL_MODES = ['ALLOW', 'DISABLE', 'PREFER', 'REQUIRE']
VALID_AUTH_MECHS = ['TD2', 'TDNEGO', 'LDAP', 'KRB5', 'JWT']
AUTH_DATA_REQUIRED = ['JWT', 'KRB5', 'LDAP']


def initialize_instance(values, **kwargs):
    if values.get('auth_mechanism') and values.get('auth_mechanism').upper() not in CREDENTIALS_OPTIONAL:
        if not values.get('username') or not values.get('password'):
            raise ValueError('`username` and `password` are required.')

    if (
        not values.get('auth_data')
        and (auth_mechanism := values.get('auth_mechanism'))
        and auth_mechanism.upper() in AUTH_DATA_REQUIRED
    ):
        raise ValueError('`auth_data` is required for auth_mechanism: {}.'.format(auth_mechanism))

    return values
