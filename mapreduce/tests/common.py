# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datadog_checks.dev import get_docker_hostname, get_here
from datadog_checks.mapreduce import MapReduceCheck

HERE = get_here()
HOST = get_docker_hostname()

# ID
APP_ID = 'application_1453738555560_0001'
APP_NAME = 'WordCount'
CONTAINER_NAME = "dd-test-mapreduce"
JOB_ID = 'job_1453738555560_0001'
JOB_NAME = 'WordCount'
USER_NAME = 'vagrant'
TASK_ID = 'task_1453738555560_0001_m_000000'
CLUSTER_NAME = 'MapReduceCluster'

# Resource manager URI
RM_URI = 'http://{}:8088'.format(HOST)

# Custom tags
CUSTOM_TAGS = ['optional:tag1']

YARN_APPS_URL_BASE = '{}/{}'.format(RM_URI, MapReduceCheck.YARN_APPS_PATH)
MR_JOBS_URL = '{}/proxy/{}/{}'.format(RM_URI, APP_ID, MapReduceCheck.MAPREDUCE_JOBS_PATH)
MR_JOB_COUNTERS_URL = '{}/{}/{}'.format(MR_JOBS_URL, JOB_ID, 'counters')
MR_TASKS_URL = '{}/{}/{}'.format(MR_JOBS_URL, JOB_ID, 'tasks')
CLUSTER_INFO_URL = '{}/{}'.format(RM_URI, MapReduceCheck.CLUSTER_INFO)

TEST_USERNAME = 'admin'
TEST_PASSWORD = 'password'

INSTANCE_INTEGRATION = {'resourcemanager_uri': RM_URI, 'cluster_name': CLUSTER_NAME, 'collect_task_metrics': True}

CLUSTER_TAG = ['cluster_name:{}'.format(CLUSTER_NAME)]

MR_CONFIG = {
    'instances': [
        {
            'resourcemanager_uri': RM_URI,
            'cluster_name': CLUSTER_NAME,
            'collect_task_metrics': 'true',
            'tags': list(CUSTOM_TAGS),
        }
    ]
}

MR_AUTH_CONFIG = {
    'instances': [
        {
            'resourcemanager_uri': RM_URI,
            'cluster_name': CLUSTER_NAME,
            'collect_task_metrics': 'true',
            'tags': list(CUSTOM_TAGS),
            'username': TEST_USERNAME,
            'password': TEST_PASSWORD,
        }
    ]
}

INIT_CONFIG = {
    'general_counters': [
        {
            'counter_group_name': 'org.apache.hadoop.mapreduce.FileSystemCounter',
            'counters': [{'counter_name': 'FILE_BYTES_READ'}, {'counter_name': 'FILE_BYTES_WRITTEN'}],
        }
    ],
    'job_specific_counters': [
        {
            'job_name': 'WordCount',
            'metrics': [
                {
                    'counter_group_name': 'org.apache.hadoop.mapreduce.FileSystemCounter',
                    'counters': [{'counter_name': 'FILE_BYTES_WRITTEN'}],
                },
                {
                    'counter_group_name': 'org.apache.hadoop.mapreduce.TaskCounter',
                    'counters': [{'counter_name': 'MAP_OUTPUT_RECORDS'}],
                },
            ],
        }
    ],
}

EXPECTED_METRICS = [
    "mapreduce.job.maps_running",
    "mapreduce.job.reduces_running",
    "mapreduce.job.failed_reduce_attempts",
    "mapreduce.job.failed_map_attempts",
    "mapreduce.job.reduces_completed",
    "mapreduce.job.reduces_pending",
    "mapreduce.job.reduces_total",
    "mapreduce.job.new_map_attempts",
    "mapreduce.job.new_reduce_attempts",
    "mapreduce.job.killed_reduce_attempts",
    "mapreduce.job.killed_map_attempts",
    "mapreduce.job.successful_reduce_attempts",
    "mapreduce.job.running_reduce_attempts",
    "mapreduce.job.running_map_attempts",
    "mapreduce.job.successful_map_attempts",
    "mapreduce.job.maps_completed",
    "mapreduce.job.maps_pending",
    "mapreduce.job.maps_total",
]

ELAPSED_TIME_BUCKET_METRICS = [
    "mapreduce.job.elapsed_time.max",
    "mapreduce.job.elapsed_time.avg",
    "mapreduce.job.elapsed_time.median",
    "mapreduce.job.elapsed_time.95percentile",
    "mapreduce.job.elapsed_time.count",
    "mapreduce.job.map.task.elapsed_time.max",
    "mapreduce.job.map.task.elapsed_time.avg",
    "mapreduce.job.map.task.elapsed_time.median",
    "mapreduce.job.map.task.elapsed_time.95percentile",
    "mapreduce.job.map.task.elapsed_time.count",
    "mapreduce.job.reduce.task.elapsed_time.max",
    "mapreduce.job.reduce.task.elapsed_time.avg",
    "mapreduce.job.reduce.task.elapsed_time.median",
    "mapreduce.job.reduce.task.elapsed_time.95percentile",
    "mapreduce.job.reduce.task.elapsed_time.count",
]

ELAPSED_TIME_METRICS = [
    "mapreduce.job.elapsed_time",
    "mapreduce.job.map.task.elapsed_time",
    "mapreduce.job.reduce.task.elapsed_time",
]

MAPREDUCE_JOB_METRIC_VALUES = {
    'mapreduce.job.elapsed_time': 99221829,
    'mapreduce.job.maps_total': 1,
    'mapreduce.job.maps_completed': 0,
    'mapreduce.job.reduces_total': 1,
    'mapreduce.job.reduces_completed': 0,
    'mapreduce.job.maps_pending': 0,
    'mapreduce.job.maps_running': 1,
    'mapreduce.job.reduces_pending': 1,
    'mapreduce.job.reduces_running': 0,
    'mapreduce.job.new_reduce_attempts': 1,
    'mapreduce.job.running_reduce_attempts': 0,
    'mapreduce.job.failed_reduce_attempts': 0,
    'mapreduce.job.killed_reduce_attempts': 0,
    'mapreduce.job.successful_reduce_attempts': 0,
    'mapreduce.job.new_map_attempts': 0,
    'mapreduce.job.running_map_attempts': 1,
    'mapreduce.job.failed_map_attempts': 1,
    'mapreduce.job.killed_map_attempts': 0,
    'mapreduce.job.successful_map_attempts': 0,
}

MAPREDUCE_JOB_METRIC_TAGS = [
    'cluster_name:{}'.format(CLUSTER_NAME),
    'app_name:{}'.format(APP_NAME),
    'job_name:{}'.format(JOB_NAME),
    'user_name:{}'.format(USER_NAME),
]

MAPREDUCE_MAP_TASK_METRIC_VALUES = {'mapreduce.job.map.task.elapsed_time': 99869037}

MAPREDUCE_MAP_TASK_METRIC_TAGS = [
    'cluster_name:{}'.format(CLUSTER_NAME),
    'app_name:{}'.format(APP_NAME),
    'job_name:{}'.format(JOB_NAME),
    'user_name:{}'.format(USER_NAME),
    'task_type:map',
]

MAPREDUCE_REDUCE_TASK_METRIC_VALUES = {'mapreduce.job.reduce.task.elapsed_time': 123456}

MAPREDUCE_REDUCE_TASK_METRIC_TAGS = [
    'cluster_name:{}'.format(CLUSTER_NAME),
    'app_name:{}'.format(APP_NAME),
    'job_name:{}'.format(JOB_NAME),
    'user_name:{}'.format(USER_NAME),
    'task_type:reduce',
]

MAPREDUCE_JOB_COUNTER_METRIC_VALUES_READ = {
    'mapreduce.job.counter.total_counter_value': {'value': 0, 'tags': ['counter_name:file_bytes_read']},
    'mapreduce.job.counter.map_counter_value': {'value': 1, 'tags': ['counter_name:file_bytes_read']},
    'mapreduce.job.counter.reduce_counter_value': {'value': 2, 'tags': ['counter_name:file_bytes_read']},
}

MAPREDUCE_JOB_COUNTER_METRIC_VALUES_WRITTEN = {
    'mapreduce.job.counter.total_counter_value': {'value': 3, 'tags': ['counter_name:file_bytes_written']},
    'mapreduce.job.counter.map_counter_value': {'value': 4, 'tags': ['counter_name:file_bytes_written']},
    'mapreduce.job.counter.reduce_counter_value': {'value': 5, 'tags': ['counter_name:file_bytes_written']},
}

MAPREDUCE_JOB_COUNTER_METRIC_VALUES_RECORDS = {
    'mapreduce.job.counter.total_counter_value': {'value': 9, 'tags': ['counter_name:map_output_records']},
    'mapreduce.job.counter.map_counter_value': {'value': 10, 'tags': ['counter_name:map_output_records']},
    'mapreduce.job.counter.reduce_counter_value': {'value': 11, 'tags': ['counter_name:map_output_records']},
}

MAPREDUCE_JOB_COUNTER_METRIC_TAGS = [
    'cluster_name:{}'.format(CLUSTER_NAME),
    'app_name:{}'.format(APP_NAME),
    'job_name:{}'.format(JOB_NAME),
    'user_name:{}'.format(USER_NAME),
]
