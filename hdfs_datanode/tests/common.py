# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname, get_here

HERE = get_here()
HOST = get_docker_hostname()
FIXTURE_DIR = os.path.join(HERE, 'fixtures')

DATANODE_URI = 'http://{}:50070/'.format(HOST)

CUSTOM_TAGS = ['optional:tag1']

TEST_USERNAME = 'AzureDiamond'
TEST_PASSWORD = 'hunter2'

INSTANCE_INTEGRATION = {"hdfs_datanode_jmx_uri": "http://{}:50075".format(HOST)}

HDFS_RAW_VERSION = os.environ.get('HDFS_RAW_VERSION')
HDFS_IMAGE_TAG = os.environ.get('HDFS_IMAGE_TAG')

EXPECTED_METRICS = [
    'hdfs.datanode.dfs_remaining',
    'hdfs.datanode.dfs_capacity',
    'hdfs.datanode.dfs_used',
    'hdfs.datanode.cache_capacity',
    'hdfs.datanode.cache_used',
    'hdfs.datanode.last_volume_failure_date',
    'hdfs.datanode.estimated_capacity_lost_total',
    'hdfs.datanode.num_blocks_cached',
    'hdfs.datanode.num_failed_volumes',
    'hdfs.datanode.num_blocks_failed_to_cache',
]

HDFS_DATANODE_CONFIG = {'instances': [{'hdfs_datanode_jmx_uri': DATANODE_URI, 'tags': list(CUSTOM_TAGS)}]}

HDFS_DATANODE_AUTH_CONFIG = {
    'instances': [
        {
            'hdfs_datanode_jmx_uri': DATANODE_URI,
            'tags': list(CUSTOM_TAGS),
            'username': TEST_USERNAME,
            'password': TEST_PASSWORD,
        }
    ]
}


HDFS_DATANODE_METRICS_VALUES = {
    'hdfs.datanode.dfs_remaining': 27914526720,
    'hdfs.datanode.dfs_capacity': 41167421440,
    'hdfs.datanode.dfs_used': 501932032,
    'hdfs.datanode.cache_capacity': 0,
    'hdfs.datanode.cache_used': 0,
    'hdfs.datanode.last_volume_failure_date': 0,
    'hdfs.datanode.estimated_capacity_lost_total': 0,
    'hdfs.datanode.num_blocks_cached': 0,
    'hdfs.datanode.num_failed_volumes': 0,
    'hdfs.datanode.num_blocks_failed_to_cache': 0,
    'hdfs.datanode.num_blocks_failed_to_uncache': 0,
}

HDFS_DATANODE_METRIC_TAGS = ['datanode_url:{}'.format(DATANODE_URI)]
