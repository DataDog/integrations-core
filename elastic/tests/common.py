# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "admin"
PASSWORD = "admin"
HOST = get_docker_hostname()
PORT = '9200'
CLUSTER_TAG = ["cluster_name:test-cluster"]
ELASTIC_CLUSTER_TAG = ["elastic_cluster:test-cluster"]
IS_OPENSEARCH = 'opensearch' in os.getenv('ELASTIC_REGISTRY')
URL = 'http://{}:{}'.format(HOST, PORT)

ELASTIC_VERSION = os.getenv('ELASTIC_VERSION', os.environ['ELASTIC_IMAGE'])

JVM_RATES = [
    'jvm.gc.collectors.young.rate',
    'jvm.gc.collectors.young.collection_time.rate',
    'jvm.gc.collectors.old.rate',
    'jvm.gc.collectors.old.collection_time.rate',
]
