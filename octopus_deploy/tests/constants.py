# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import os

from datadog_checks.base.utils.time import ensure_aware_datetime
from datadog_checks.dev.fs import get_here

COMPOSE_FILE = os.path.join(get_here(), 'docker', 'docker-compose.yaml')
INSTANCE = {'octopus_endpoint': 'http://localhost:80/api', 'space': 'Default'}


BASE_TIME = ensure_aware_datetime(datetime.datetime.strptime("2024-09-23 14:45:58.888492", '%Y-%m-%d %H:%M:%S.%f'))
MOCKED_TIMESTAMPS = [BASE_TIME] * 20


ALL_METRICS = [
    "octopus_deploy.project_group.count",
    "octopus_deploy.project.count",
    "octopus_deploy.deployment.count",
    "octopus_deploy.deployment.duration",
    "octopus_deploy.deployment.queue_time",
    "octopus_deploy.deployment.succeeded",
    "octopus_deploy.deployment.can_rerun",
]

PROJECT_GROUP_ALL_METRICS = [
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:Default Project Group", "project_group_id:ProjectGroups-1", "space_name:Default"],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:hello", "project_group_id:ProjectGroups-3", "space_name:Default"],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:test-group", "project_group_id:ProjectGroups-2", "space_name:Default"],
        'count': 1,
    },
]

PROJECT_GROUP_ONLY_TEST_GROUP_METRICS = [
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:Default Project Group", "project_group_id:ProjectGroups-1", "space_name:Default"],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:hello", "project_group_id:ProjectGroups-3", "space_name:Default"],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:test-group", "project_group_id:ProjectGroups-2", "space_name:Default"],
        'count': 1,
    },
]

PROJECT_GROUP_NO_METRICS = [
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:Default Project Group", "project_group_id:ProjectGroups-1", "space_name:Default"],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:hello", "project_group_id:ProjectGroups-3", "space_name:Default"],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:test-group", "project_group_id:ProjectGroups-2", "space_name:Default"],
        'count': 0,
    },
]
PROJECT_GROUP_NO_TEST_GROUP_METRICS = [
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:Default Project Group", "project_group_id:ProjectGroups-1", "space_name:Default"],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:hello", "project_group_id:ProjectGroups-3", "space_name:Default"],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project_group.count',
        'tags': ["project_group_name:test-group", "project_group_id:ProjectGroups-2", "space_name:Default"],
        'count': 0,
    },
]

PROJECT_ALL_METRICS = [
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:test-group",
            "project_group_id:ProjectGroups-2",
            "space_name:Default",
            "project_name:hi",
            "project_id:Projects-4",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:my-project",
            "project_id:Projects-2",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
        ],
        'count': 1,
    },
]

PROJECT_ONLY_TEST_GROUP_METRICS = [
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:test-group",
            "project_group_id:ProjectGroups-2",
            "space_name:Default",
            "project_name:hi",
            "project_id:Projects-4",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:my-project",
            "project_id:Projects-2",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
        ],
        'count': 0,
    },
]

PROJECT_ONLY_DEFAULT_GROUP_METRICS = [
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:test-group",
            "project_group_id:ProjectGroups-2",
            "space_name:Default",
            "project_name:hi",
            "project_id:Projects-4",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:my-project",
            "project_id:Projects-2",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
        ],
        'count': 1,
    },
]

PROJECT_ONLY_TEST_METRICS = [
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:test-group",
            "project_group_id:ProjectGroups-2",
            "space_name:Default",
            "project_name:hi",
            "project_id:Projects-4",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:my-project",
            "project_id:Projects-2",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
        ],
        'count': 1,
    },
]

PROJECT_ONLY_HI_METRICS = [
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:test-group",
            "project_group_id:ProjectGroups-2",
            "space_name:Default",
            "project_name:hi",
            "project_id:Projects-4",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:my-project",
            "project_id:Projects-2",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
        ],
        'count': 0,
    },
]

PROJECT_ONLY_HI_MY_PROJECT_METRICS = [
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:test-group",
            "project_group_id:ProjectGroups-2",
            "space_name:Default",
            "project_name:hi",
            "project_id:Projects-4",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:my-project",
            "project_id:Projects-2",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
        ],
        'count': 0,
    },
]

PROJECT_EXCLUDE_TEST_API_METRICS = [
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:test-group",
            "project_group_id:ProjectGroups-2",
            "space_name:Default",
            "project_name:hi",
            "project_id:Projects-4",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:my-project",
            "project_id:Projects-2",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
        ],
        'count': 0,
    },
]

PROJECT_NO_METRICS = [
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:test-group",
            "project_group_id:ProjectGroups-2",
            "space_name:Default",
            "project_name:hi",
            "project_id:Projects-4",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:my-project",
            "project_id:Projects-2",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
        ],
        'count': 0,
    },
    {
        'name': 'octopus_deploy.project.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
        ],
        'count': 0,
    },
]


DEPLOYMENT_METRICS = [
    {
        'name': 'octopus_deploy.deployment.duration',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1845",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 2.073,
    },
    {
        'name': 'octopus_deploy.deployment.queue_time',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1845",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 0.639,
    },
    {
        'name': 'octopus_deploy.deployment.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 1,
    },
    {
        'name': 'octopus_deploy.deployment.succeeded',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 1,
    },
    {
        'name': 'octopus_deploy.deployment.can_rerun',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 0,
    },
    {
        'name': 'octopus_deploy.deployment.duration',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 2.134,
    },
    {
        'name': 'octopus_deploy.deployment.queue_time',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 0.67,
    },
    {
        'name': 'octopus_deploy.deployment.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
        'value': 1,
    },
    {
        'name': 'octopus_deploy.deployment.succeeded',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
        'value': 0,
    },
    {
        'name': 'octopus_deploy.deployment.can_rerun',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
        'value': 0,
    },
    {
        'name': 'octopus_deploy.deployment.duration',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
        'value': 6.267,
    },
    {
        'name': 'octopus_deploy.deployment.queue_time',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
        'value': 0.631,
    },
    {
        'name': 'octopus_deploy.deployment.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
            "task_id:ServerTasks-1844",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 1,
    },
    {
        'name': 'octopus_deploy.deployment.succeeded',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
            "task_id:ServerTasks-1844",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 1,
    },
    {
        'name': 'octopus_deploy.deployment.can_rerun',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
            "task_id:ServerTasks-1844",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 0,
    },
    {
        'name': 'octopus_deploy.deployment.duration',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
            "task_id:ServerTasks-1844",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 3.192,
    },
    {
        'name': 'octopus_deploy.deployment.queue_time',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test-api",
            "project_id:Projects-1",
            "task_id:ServerTasks-1844",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
        'value': 0.613,
    },
]


DEPLOYMENT_METRICS_NO_PROJECT_1 = [
    {
        'name': 'octopus_deploy.deployment.duration',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1845",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.queue_time',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1845",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.succeeded',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.can_rerun',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.duration',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.queue_time',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1846",
            "task_name:Deploy",
            "task_state:Success",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.count',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.succeeded',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.can_rerun',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.duration',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
    },
    {
        'name': 'octopus_deploy.deployment.queue_time',
        'tags': [
            "project_group_name:Default Project Group",
            "project_group_id:ProjectGroups-1",
            "space_name:Default",
            "project_name:test",
            "project_id:Projects-3",
            "task_id:ServerTasks-1847",
            "task_name:Deploy",
            "task_state:Failed",
        ],
        'count': 1,
    },
]
