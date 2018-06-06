# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

HERE = os.path.dirname(os.path.abspath(__file__))

DATANODE_URI = 'http://localhost:50070/'

CUSTOM_TAGS = ['optional:tag1']

TEST_USERNAME = 'AzureDiamond'
TEST_PASSWORD = 'hunter2'

HDFS_DATANODE_CONFIG = {
    'instances': [
        {
            'hdfs_datanode_jmx_uri': DATANODE_URI,
            'tags': list(CUSTOM_TAGS)
        }
    ]
}

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

HDFS_DATANODE_METRIC_TAGS = [
    'datanode_url:{}'.format(DATANODE_URI),
]
