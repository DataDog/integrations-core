# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    # kafka_connect_str may be passed as a list of broker strings (e.g. from kafka_consumer config
    # via autodiscovery). Normalize to a comma-separated string for librdkafka's bootstrap.servers.
    kafka_connect_str = values.get('kafka_connect_str')
    if isinstance(kafka_connect_str, list):
        values['kafka_connect_str'] = ','.join(str(s) for s in kafka_connect_str)

    return values
