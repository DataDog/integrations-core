# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Namenode URI
NAMENODE_URI = 'http://localhost:50070/'
NAMENODE_JMX_URI = NAMENODE_URI + 'jmx'

# Namesystem state URL
NAME_SYSTEM_STATE_URL = NAMENODE_JMX_URI + '?qry=Hadoop:service=NameNode,name=FSNamesystemState'

# Namesystem url
NAME_SYSTEM_URL = NAMENODE_JMX_URI + '?qry=Hadoop:service=NameNode,name=FSNamesystem'

CUSTOM_TAGS = ["cluster_name:hdfs_dev", "instance:level_tags"]

# Authentication Parameters
TEST_USERNAME = 'Picard'
TEST_PASSWORD = 'NCC-1701'

HDFS_NAMENODE_CONFIG = {
    'instances': [
        {
            'hdfs_namenode_jmx_uri': NAMENODE_URI,
            'tags': list(CUSTOM_TAGS)
        }
    ]
}

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

HDFS_NAMESYSTEM_METRICS_VALUES = {
    'hdfs.namenode.missing_blocks': 0,
    'hdfs.namenode.corrupt_blocks': 1,
}

HDFS_NAMESYSTEM_MUTUAL_METRICS_VALUES = {
    'hdfs.namenode.capacity_in_use': None
}

HDFS_NAMESYSTEM_METRIC_TAGS = ['namenode_url:' + NAMENODE_URI]
