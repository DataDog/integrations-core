# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_docker_hostname, get_here, load_jmx_config

HERE = get_here()
HOST = get_docker_hostname()

INSTANCES = [
    {'host': 'localhost', 'port': '31000'},  # confluentinc/cp-zookeeper
    {'host': 'localhost', 'port': '31001'},  # confluentinc/cp-server
    {'host': 'localhost', 'port': '31002'},  # cnfldemos/cp-server-connect-datagen
    {'host': 'localhost', 'port': '31004'},  # confluentinc/cp-ksql-server
    {'host': 'localhost', 'port': '31006'},  # confluentinc/cp-kafka-rest
    {'host': 'localhost', 'port': '31007'},  # confluentinc/cp-schema-registry
    {'host': 'localhost', 'port': '31008'},  # confluentinc/cp-enterprise-replicator
]

CHECK_CONFIG = load_jmx_config()
CHECK_CONFIG['instances'] = INSTANCES
