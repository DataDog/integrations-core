# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from datadog_checks.utils.common import get_docker_hostname

CHECK_NAME = "elastic"

HERE = os.path.dirname(os.path.abspath(__file__))
USER = "elastic"
PASSWORD = "changeme"
HOST = get_docker_hostname()
PORT = '9200'
BAD_PORT = '9405'
CONF_HOSTNAME = "foo"
TAGS = [u"foo:bar", u"baz"]
CLUSTER_TAG = [u"cluster_name:elasticsearch"]
URL = 'http://{0}:{1}'.format(HOST, PORT)
BAD_URL = 'http://{0}:{1}'.format(HOST, BAD_PORT)

CONFIG = {'url': URL, 'username': USER, 'password': PASSWORD, 'tags': TAGS}
BAD_CONFIG = {'url': BAD_URL, 'password': PASSWORD}

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


def get_es_version():
    version = os.environ.get("ELASTIC_VERSION")
    dd_versions = {'0_90': [0, 90, 13], '1_0': [1, 0, 3], '1_1': [1, 1, 2], '1_2': [1, 2, 4]}
    if version is None:
        return [6, 0, 1]
    if '_' in version:
        return dd_versions[version]
    else:
        return [int(k) for k in version.split(".")]
