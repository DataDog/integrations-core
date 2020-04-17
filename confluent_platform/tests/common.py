# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_docker_hostname, get_here, load_jmx_config

HERE = get_here()
HOST = get_docker_hostname()

DEFAULT_MAX_RETURNED_METRICS = 2000

INSTANCES = [
    {
        'host': 'localhost',
        'port': '31000',
        'max_returned_metrics': DEFAULT_MAX_RETURNED_METRICS,
    },  # confluentinc/cp-zookeeper
    {
        'host': 'localhost',
        'port': '31001',
        'max_returned_metrics': DEFAULT_MAX_RETURNED_METRICS,
    },  # confluentinc/cp-server
    {
        'host': 'localhost',
        'port': '31002',
        'max_returned_metrics': DEFAULT_MAX_RETURNED_METRICS,
    },  # cnfldemos/cp-server-connect-datagen
    {
        'host': 'localhost',
        'port': '31004',
        'max_returned_metrics': DEFAULT_MAX_RETURNED_METRICS,
    },  # confluentinc/cp-ksql-server
    {
        'host': 'localhost',
        'port': '31006',
        'max_returned_metrics': DEFAULT_MAX_RETURNED_METRICS,
    },  # confluentinc/cp-kafka-rest
    {
        'host': 'localhost',
        'port': '31007',
        'max_returned_metrics': DEFAULT_MAX_RETURNED_METRICS,
    },  # confluentinc/cp-schema-registry
    {
        'host': 'localhost',
        'port': '31008',
        'max_returned_metrics': DEFAULT_MAX_RETURNED_METRICS,
    },  # confluentinc/cp-enterprise-replicator
]

CHECK_CONFIG = load_jmx_config()
CHECK_CONFIG['instances'] = INSTANCES
CHECK_CONFIG['init_config']['collect_default_metrics'] = False
