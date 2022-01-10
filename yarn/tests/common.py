# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import os

from datadog_checks.dev import get_docker_hostname
from datadog_checks.yarn.yarn import YARN_APPS_PATH, YARN_CLUSTER_METRICS_PATH, YARN_NODES_PATH, YARN_SCHEDULER_PATH

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE_DIR = os.path.join(HERE, 'fixtures')

# IDs
CLUSTER_NAME = 'SparkCluster'

# Resource manager URI
RM_ADDRESS = 'http://{}:8088'.format(get_docker_hostname())

# Service URLs
YARN_CLUSTER_METRICS_URL = '{}{}'.format(RM_ADDRESS, YARN_CLUSTER_METRICS_PATH)
YARN_APPS_URL = '{}{}'.format(RM_ADDRESS, YARN_APPS_PATH)
YARN_NODES_URL = '{}{}'.format(RM_ADDRESS, YARN_NODES_PATH)
YARN_SCHEDULER_URL = '{}{}'.format(RM_ADDRESS, YARN_SCHEDULER_PATH)

CUSTOM_TAGS = ['optional:tag1']

TEST_USERNAME = 'admin'
TEST_PASSWORD = 'password'

INSTANCE_INTEGRATION = {
    "resourcemanager_uri": RM_ADDRESS,
    "cluster_name": CLUSTER_NAME,
}

LEGACY_CLUSTER_TAG = "cluster_name:{}".format(CLUSTER_NAME)
YARN_CLUSTER_TAG = "yarn_cluster:{}".format(CLUSTER_NAME)

EXPECTED_METRICS = [
    "yarn.metrics.apps_submitted",
    "yarn.metrics.apps_completed",
    "yarn.metrics.apps_pending",
    "yarn.metrics.apps_running",
    "yarn.metrics.apps_failed",
    "yarn.metrics.apps_killed",
    "yarn.metrics.reserved_mb",
    "yarn.metrics.available_mb",
    "yarn.metrics.allocated_mb",
    "yarn.metrics.total_mb",
    "yarn.metrics.reserved_virtual_cores",
    "yarn.metrics.available_virtual_cores",
    "yarn.metrics.allocated_virtual_cores",
    "yarn.metrics.total_virtual_cores",
    "yarn.metrics.containers_allocated",
    "yarn.metrics.containers_reserved",
    "yarn.metrics.containers_pending",
    "yarn.metrics.total_nodes",
    "yarn.metrics.active_nodes",
    "yarn.metrics.lost_nodes",
    "yarn.metrics.unhealthy_nodes",
    "yarn.metrics.decommissioned_nodes",
    "yarn.metrics.rebooted_nodes",
    "yarn.queue.root.max_capacity",
    "yarn.queue.root.used_capacity",
    "yarn.queue.root.capacity",
    "yarn.queue.num_pending_applications",
    "yarn.queue.user_am_resource_limit.memory",
    "yarn.queue.user_am_resource_limit.vcores",
    "yarn.queue.absolute_capacity",
    "yarn.queue.user_limit_factor",
    "yarn.queue.user_limit",
    "yarn.queue.num_applications",
    "yarn.queue.used_am_resource.memory",
    "yarn.queue.used_am_resource.vcores",
    "yarn.queue.absolute_used_capacity",
    "yarn.queue.resources_used.memory",
    "yarn.queue.resources_used.vcores",
    "yarn.queue.am_resource_limit.vcores",
    "yarn.queue.am_resource_limit.memory",
    "yarn.queue.capacity",
    "yarn.queue.num_active_applications",
    "yarn.queue.absolute_max_capacity",
    "yarn.queue.used_capacity",
    "yarn.queue.num_containers",
    "yarn.queue.max_capacity",
    "yarn.queue.max_applications",
    "yarn.queue.max_applications_per_user",
    "yarn.node.last_health_update",
    "yarn.node.used_memory_mb",
    "yarn.node.avail_memory_mb",
    "yarn.node.used_virtual_cores",
    "yarn.node.available_virtual_cores",
    "yarn.node.num_containers",
]

EXPECTED_TAGS = ['cluster_name:test', 'yarn_cluster:test']

YARN_CONFIG = {
    'instances': [
        {
            'resourcemanager_uri': RM_ADDRESS,
            'cluster_name': CLUSTER_NAME,
            'tags': list(CUSTOM_TAGS),
            'application_tags': {'app_id': 'id', 'app_queue': 'queue'},
            'queue_blacklist': ['nofollowqueue'],
        }
    ]
}

YARN_CONFIG_STATUS_MAPPING = {
    'instances': [
        {
            'resourcemanager_uri': RM_ADDRESS,
            'cluster_name': CLUSTER_NAME,
            'tags': list(CUSTOM_TAGS),
            'application_tags': {'app_id': 'id', 'app_queue': 'queue'},
            'queue_blacklist': ['nofollowqueue'],
            "application_status_mapping": {
                'ALL': 'unknown',
                'NEW': 'ok',
                'NEW_SAVING': 'ok',
                'SUBMITTED': 'ok',
                'ACCEPTED': 'ok',
                'RUNNING': 'ok',
                'FINISHED': 'ok',
                'FAILED': 'warning',
                'KILLED': 'warning',
            },
        }
    ]
}

YARN_CONFIG_EXCLUDING_APP = {
    'instances': [
        {
            'resourcemanager_uri': RM_ADDRESS,
            'cluster_name': CLUSTER_NAME,
            'tags': list(CUSTOM_TAGS),
            'application_tags': {'app_id': 'id', 'app_queue': 'queue'},
            'collect_app_metrics': 'false',
        }
    ]
}

YARN_CONFIG_SPLIT_APPLICATION_TAGS = {
    'instances': [
        {
            'resourcemanager_uri': RM_ADDRESS,
            'cluster_name': CLUSTER_NAME,
            'tags': list(CUSTOM_TAGS),
            'application_tags': {'app_id': 'id', 'app_queue': 'queue', 'app_tags': 'applicationTags'},
            'split_yarn_application_tags': 'true',
            "application_status_mapping": {
                'ALL': 'unknown',
                'NEW': 'ok',
                'NEW_SAVING': 'ok',
                'SUBMITTED': 'ok',
                'ACCEPTED': 'ok',
                'RUNNING': 'ok',
                'FINISHED': 'ok',
                'FAILED': 'warning',
                'KILLED': 'warning',
            },
        }
    ]
}

YARN_AUTH_CONFIG = {
    'instances': [
        {
            'resourcemanager_uri': RM_ADDRESS,
            'cluster_name': CLUSTER_NAME,
            'tags': list(CUSTOM_TAGS),
            'application_tags': {'app_id': 'id', 'app_queue': 'queue'},
            'username': TEST_USERNAME,
            'password': TEST_PASSWORD,
        }
    ]
}

YARN_SSL_VERIFY_TRUE_CONFIG = {
    'instances': [
        {
            'resourcemanager_uri': RM_ADDRESS,
            'cluster_name': CLUSTER_NAME,
            'tags': list(CUSTOM_TAGS),
            'application_tags': {'app_id': 'id', 'app_queue': 'queue'},
            'ssl_verify': True,
        }
    ]
}

YARN_SSL_VERIFY_FALSE_CONFIG = {
    'instances': [
        {
            'resourcemanager_uri': RM_ADDRESS,
            'cluster_name': CLUSTER_NAME,
            'tags': list(CUSTOM_TAGS),
            'application_tags': {'app_id': 'id', 'app_queue': 'queue'},
            'ssl_verify': False,
        }
    ]
}

YARN_CLUSTER_METRICS_VALUES = {
    'yarn.metrics.apps_submitted': 0,
    'yarn.metrics.apps_completed': 0,
    'yarn.metrics.apps_pending': 0,
    'yarn.metrics.apps_running': 0,
    'yarn.metrics.apps_failed': 0,
    'yarn.metrics.apps_killed': 0,
    'yarn.metrics.reserved_mb': 0,
    'yarn.metrics.available_mb': 17408,
    'yarn.metrics.allocated_mb': 0,
    'yarn.metrics.total_mb': 17408,
    'yarn.metrics.reserved_virtual_cores': 0,
    'yarn.metrics.available_virtual_cores': 7,
    'yarn.metrics.allocated_virtual_cores': 1,
    'yarn.metrics.total_virtual_cores': 8,
    'yarn.metrics.containers_allocated': 0,
    'yarn.metrics.containers_reserved': 0,
    'yarn.metrics.containers_pending': 0,
    'yarn.metrics.total_nodes': 1,
    'yarn.metrics.active_nodes': 1,
    'yarn.metrics.lost_nodes': 0,
    'yarn.metrics.unhealthy_nodes': 0,
    'yarn.metrics.decommissioned_nodes': 0,
    'yarn.metrics.rebooted_nodes': 0,
}

YARN_CLUSTER_METRICS_TAGS = [LEGACY_CLUSTER_TAG, YARN_CLUSTER_TAG]

DEPRECATED_YARN_APP_METRICS_VALUES = {
    'yarn.apps.progress': 100,
    'yarn.apps.started_time': 1326815573334,
    'yarn.apps.finished_time': 1326815598530,
    'yarn.apps.elapsed_time': 25196,
    'yarn.apps.allocated_mb': 0,
    'yarn.apps.allocated_vcores': 0,
    'yarn.apps.running_containers': 0,
    'yarn.apps.memory_seconds': 151730,
    'yarn.apps.vcore_seconds': 103,
}

YARN_APP_METRICS_VALUES = {
    'yarn.apps.progress_gauge': 100,
    'yarn.apps.started_time_gauge': 1326815573334,
    'yarn.apps.finished_time_gauge': 1326815598530,
    'yarn.apps.elapsed_time_gauge': 25196,
    'yarn.apps.allocated_mb_gauge': 0,
    'yarn.apps.allocated_vcores_gauge': 0,
    'yarn.apps.running_containers_gauge': 0,
    'yarn.apps.memory_seconds_gauge': 151730,
    'yarn.apps.vcore_seconds_gauge': 103,
}

YARN_APP_METRICS_TAGS = ['app_name:word count', 'app_queue:default'] + YARN_CLUSTER_METRICS_TAGS

YARN_NODE_METRICS_VALUES = {
    'yarn.node.last_health_update': 1324056895432,
    'yarn.node.used_memory_mb': 0,
    'yarn.node.avail_memory_mb': 8192,
    'yarn.node.used_virtual_cores': 0,
    'yarn.node.available_virtual_cores': 8,
    'yarn.node.num_containers': 0,
}

YARN_NODE_METRICS_TAGS = ['node_id:h2:1235'] + YARN_CLUSTER_METRICS_TAGS

YARN_ROOT_QUEUE_METRICS_VALUES = {
    'yarn.queue.root.max_capacity': 100,
    'yarn.queue.root.used_capacity': 35.012,
    'yarn.queue.root.capacity': 100,
}

YARN_ROOT_QUEUE_METRICS_TAGS = ['queue_name:root'] + YARN_CLUSTER_METRICS_TAGS

YARN_QUEUE_METRICS_VALUES = {
    'yarn.queue.num_pending_applications': 0,
    'yarn.queue.user_am_resource_limit.memory': 2587968,
    'yarn.queue.user_am_resource_limit.vcores': 688,
    'yarn.queue.absolute_capacity': 52.12,
    'yarn.queue.user_limit_factor': 1,
    'yarn.queue.user_limit': 100,
    'yarn.queue.num_applications': 3,
    'yarn.queue.used_am_resource.memory': 2688,
    'yarn.queue.used_am_resource.vcores': 3,
    'yarn.queue.absolute_used_capacity': 31.868685,
    'yarn.queue.resources_used.memory': 3164800,
    'yarn.queue.resources_used.vcores': 579,
    'yarn.queue.am_resource_limit.vcores': 688,
    'yarn.queue.am_resource_limit.memory': 2587968,
    'yarn.queue.capacity': 52.12,
    'yarn.queue.num_active_applications': 3,
    'yarn.queue.absolute_max_capacity': 52.12,
    'yarn.queue.used_capacity': 61.14484,
    'yarn.queue.num_containers': 75,
    'yarn.queue.max_capacity': 52.12,
    'yarn.queue.max_applications': 5212,
    'yarn.queue.max_applications_per_user': 5212,
}

YARN_QUEUE_METRICS_TAGS = ['queue_name:clientqueue'] + YARN_CLUSTER_METRICS_TAGS

YARN_QUEUE_NOFOLLOW_METRICS_TAGS = ['queue_name:nofollowqueue'] + YARN_CLUSTER_METRICS_TAGS
