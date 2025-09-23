# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.dev import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
COMPOSE_FILE = os.path.join(HERE, 'docker', 'docker-compose.yaml')
HOST = get_docker_hostname()
PORT = '23790'
URL = 'http://{}:{}'.format(HOST, PORT)

LEGACY_INSTANCE = {'url': URL, 'use_preview': False}

ETCD_VERSION = os.getenv('ETCD_VERSION')

REMAPED_DEBUGGING_METRICS = [
    'debugging.mvcc.db.total.size.in_bytes',
    'debugging.mvcc.delete.total',
    'debugging.mvcc.put.total',
    'debugging.mvcc.range.total',
    'debugging.mvcc.txn.total',
]

STORE_METRICS = [
    'compareanddelete.fail',
    'compareanddelete.success',
    'compareandswap.fail',
    'compareandswap.success',
    'create.fail',
    'create.success',
    'delete.fail',
    'delete.success',
    'expire.count',
    'gets.fail',
    'gets.success',
    'sets.fail',
    'sets.success',
    'update.fail',
    'update.success',
    'watchers',
]
