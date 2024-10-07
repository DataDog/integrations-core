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

DEPLOY_SUCCESS_STATE = "Success"
