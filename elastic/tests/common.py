# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.utils.common import get_docker_hostname

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "elastic"
PASSWORD = "changeme"
HOST = get_docker_hostname()
PORT = '9200'
BAD_PORT = '9405'
CLUSTER_TAG = ["cluster_name:test-cluster"]
URL = 'http://{}:{}'.format(HOST, PORT)
BAD_URL = 'http://{}:{}'.format(HOST, BAD_PORT)


TEST_INSTANCE = {
    'url': URL,
    'username': USER,
    'password': PASSWORD,
    'tags': ["foo:bar", "baz"]
}

INDEX_METRICS_MOCK_DATA = [{
        "health": "green",
        "status": "open",
        "index": "index_1",
        "uuid": "GFgeYjVISAu6MMF2fKVkXQ",
        "pri": "1",
        "rep": "2",
        "docs.count": "66354395",
        "docs.deleted": "0",
        "store.size": "29.2",
        "pri.store.size": "9.7"
    },
    {
        "health": "green",
        "status": "open",
        "index": "index_2",
        "uuid": "_szXbRJtSKG9Q58PrO6Tqg",
        "pri": "1",
        "rep": "2",
        "docs.count": "50678201",
        "docs.deleted": "0",
        "store.size": "31.7",
        "pri.store.size": "10.5"
    },
]
