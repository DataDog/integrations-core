# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

ALL_METRICS = ["octopus_deploy.project_group.count", "octopus_deploy.space.count"]

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
