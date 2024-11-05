# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

API_UP_METRIC = "api.can_connect"
SPACE_COUNT_METRIC = "space.count"
PROJECT_GROUP_COUNT_METRIC = "project_group.count"
PROJECT_COUNT_METRIC = "project.count"
DEPLOY_PREFIX = "deployment"
DEPLOY_COUNT_METRIC = f"{DEPLOY_PREFIX}.count"
DEPLOY_DURATION_METRIC = f"{DEPLOY_PREFIX}.duration"
DEPLOY_QUEUE_TIME_METRIC = f"{DEPLOY_PREFIX}.queue_time"
DEPLOY_SUCCESS_METRIC = f"{DEPLOY_PREFIX}.succeeded"
DEPLOY_RERUN_METRIC = f"{DEPLOY_PREFIX}.can_rerun"
DEPLOY_WARNINGS_METRIC = f"{DEPLOY_PREFIX}.has_warnings_or_errors"
DEPLOY_QUEUED_METRIC = f"{DEPLOY_PREFIX}.queued"
DEPLOY_RUNNING_METRIC = f"{DEPLOY_PREFIX}.running"

SERVER_PREFIX = "server_node"
SERVER_COUNT_METRIC = f"{SERVER_PREFIX}.count"
SERVER_MAINTENANCE_MODE_METRIC = f"{SERVER_PREFIX}.in_maintenance_mode"
SERVER_MAX_TASKS_METRIC = f"{SERVER_PREFIX}.max_concurrent_tasks"

DEPLOY_SUCCESS_STATE = "Success"
DEPLOY_RUNNING_STATE = "Executing"
DEPLOY_QUEUED_STATE = "Queued"
