# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.time import get_current_datetime


class ProjectGroup:
    def __init__(self, project_group_json):
        self.id = project_group_json.get("Id")
        self.name = project_group_json.get("Name")
        self.projects = None


class Project:
    def __init__(self, project_json, project_group):
        self.id = project_json.get("Id")
        self.name = project_json.get("Name")
        self.project_group = project_group
        self.last_task_time = get_current_datetime()
