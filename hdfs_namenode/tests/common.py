# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_here
from datadog_checks.dev.docker import get_docker_hostname

HERE = get_here()
HOST = get_docker_hostname()
FIXTURE_DIR = os.path.join(HERE, 'fixtures')

# Namenode URI
NAMENODE_URI = 'http://{}:50070/'.format(HOST)
NAMENODE_JMX_URI = NAMENODE_URI + 'jmx'

# Namesystem state URL
NAME_SYSTEM_STATE_URL = NAMENODE_JMX_URI + '?qry=Hadoop:service=NameNode,name=FSNamesystemState'

# Namesystem url
NAME_SYSTEM_URL = NAMENODE_JMX_URI + '?qry=Hadoop:service=NameNode,name=FSNamesystem'

# Namesystem metadata url
NAME_SYSTEM_METADATA_URL = NAMENODE_JMX_URI + '?qry=Hadoop:service=NameNode,name=NameNodeInfo'

CUSTOM_TAGS = ["hdfs_cluster:hdfs_dev", "instance:level_tags"]

# Authentication Parameters
TEST_USERNAME = 'Picard'
TEST_PASSWORD = 'NCC-1701'

HDFS_NAMENODE_CONFIG = {'instances': [{'hdfs_namenode_jmx_uri': NAMENODE_URI, 'tags': list(CUSTOM_TAGS)}]}

INSTANCE_INTEGRATION = {'hdfs_namenode_jmx_uri': NAMENODE_URI}

HDFS_RAW_VERSION = os.environ.get('HDFS_RAW_VERSION')
HDFS_IMAGE_TAG = os.environ.get('HDFS_IMAGE_TAG')

EXPECTED_METRICS = [
    'hdfs.namenode.capacity_total',
    'hdfs.namenode.capacity_used',
    'hdfs.namenode.capacity_remaining',
    'hdfs.namenode.capacity_in_use',
    'hdfs.namenode.total_load',
    'hdfs.namenode.blocks_total',
    'hdfs.namenode.max_objects',
    'hdfs.namenode.files_total',
    'hdfs.namenode.pending_replication_blocks',
    'hdfs.namenode.under_replicated_blocks',
    'hdfs.namenode.scheduled_replication_blocks',
    'hdfs.namenode.pending_deletion_blocks',
    'hdfs.namenode.num_live_data_nodes',
    'hdfs.namenode.num_dead_data_nodes',
    'hdfs.namenode.num_decom_live_data_nodes',
    'hdfs.namenode.num_decom_dead_data_nodes',
    'hdfs.namenode.volume_failures_total',
    'hdfs.namenode.estimated_capacity_lost_total',
    'hdfs.namenode.num_decommissioning_data_nodes',
    'hdfs.namenode.num_stale_data_nodes',
    'hdfs.namenode.num_stale_storages',
    'hdfs.namenode.missing_blocks',
    'hdfs.namenode.corrupt_blocks',
]

HDFS_NAMENODE_AUTH_CONFIG = {
    'instances': [
        {
            'hdfs_namenode_jmx_uri': NAMENODE_URI,
            'tags': list(CUSTOM_TAGS),
            'username': TEST_USERNAME,
            'password': TEST_PASSWORD,
        }
    ]
}

HDFS_NAMESYSTEM_STATE_METRICS_VALUES = {
    'hdfs.namenode.capacity_total': 41167421440,
    'hdfs.namenode.capacity_used': 501932032,
    'hdfs.namenode.capacity_remaining': 27878948864,
    'hdfs.namenode.total_load': 2,
    'hdfs.namenode.fs_lock_queue_length': 0,
    'hdfs.namenode.blocks_total': 27661,
    'hdfs.namenode.max_objects': 0,
    'hdfs.namenode.files_total': 82950,
    'hdfs.namenode.pending_replication_blocks': 0,
    'hdfs.namenode.under_replicated_blocks': 27661,
    'hdfs.namenode.scheduled_replication_blocks': 0,
    'hdfs.namenode.pending_deletion_blocks': 0,
    'hdfs.namenode.num_live_data_nodes': 1,
    'hdfs.namenode.num_dead_data_nodes': 0,
    'hdfs.namenode.num_decom_live_data_nodes': 0,
    'hdfs.namenode.num_decom_dead_data_nodes': 0,
    'hdfs.namenode.volume_failures_total': 0,
    'hdfs.namenode.estimated_capacity_lost_total': 0,
    'hdfs.namenode.num_decommissioning_data_nodes': 0,
    'hdfs.namenode.num_stale_data_nodes': 0,
    'hdfs.namenode.num_stale_storages': 0,
}

HDFS_NAMESYSTEM_METRICS_VALUES = {'hdfs.namenode.missing_blocks': 0, 'hdfs.namenode.corrupt_blocks': 1}

HDFS_NAMESYSTEM_MUTUAL_METRICS_VALUES = {'hdfs.namenode.capacity_in_use': None}

HDFS_NAMESYSTEM_METRIC_TAGS = ['namenode_url:' + NAMENODE_URI]
