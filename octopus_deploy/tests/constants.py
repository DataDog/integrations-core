# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

ALL_METRICS = ["octopus_deploy.project_group.count", "octopus_deploy.project.count", "octopus_deploy.space.count"]

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
