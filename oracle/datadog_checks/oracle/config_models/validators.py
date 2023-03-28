# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.oracle.oracle import PROTOCOL_TCPS, VALID_PROTOCOLS, VALID_TRUSTSTORE_TYPES


def initialize_instance(values, **kwargs):
    # TODO: remove when deprecation is finalized https://github.com/DataDog/integrations-core/pull/9340
    if 'username' not in values and 'user' in values:
        values['username'] = values['user']

    if not values.get('server') or not values.get('username'):
        raise ValueError('Oracle host and user are needed')

    if values.get('jdbc_driver_path') and values.get('use_instant_client'):
        raise ValueError(
            'Oracle Instant Client and Oracle JDBC configured. Use either `use_instant_client` or `jdbc_driver_path`'
        )

    protocol = values.get('protocol', 'TCP')
    if not protocol or protocol.upper() not in VALID_PROTOCOLS:
        raise ValueError('Protocol %s is not valid, must either be TCP or TCPS' % protocol)

    if values.get('jdbc_driver_path') and protocol == PROTOCOL_TCPS:
        if not (values.get('jdbc_truststore_type') and values.get('jdbc_truststore_path')):
            raise ValueError(
                "TCPS connections to Oracle via JDBC requires both `jdbc_truststore_type` and "
                "`jdbc_truststore_path` configuration options"
            )
        if (
            values.get('jdbc_truststore_type')
            and values.get('jdbc_truststore_type').upper() not in VALID_TRUSTSTORE_TYPES
        ):
            raise ValueError(
                "Truststore type %s is not valid, must be one of %s"
                % (values.get('jdbc_truststore_type'), VALID_TRUSTSTORE_TYPES)
            )

    return values
