# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from copy import deepcopy


class Build(object):
    def __init__(self, build_id):
        self.build_id = build_id


class BuildConfig(object):
    def __init__(self, build_config_id):
        self.build_config_id = build_config_id
        self.last_build_id = None
        self.build_config_type = None

    def get(self, attribute, default=None):
        if attribute in self:
            return self.getattr(attribute)
        else:
            return default


class BuildConfigs(BuildConfig):
    def __init__(self):
        self.build_configs = {}

    def get_all_build_configs(self):
        return deepcopy(self.build_configs)

    def get_build_configs(self, project_id):
        if self.build_configs.get(project_id):
            return deepcopy(self.build_configs[project_id])

    def set_build_config(self, project_id, build_config_id, build_config_type=None):
        if not self.build_configs.get(project_id):
            self.build_configs[project_id] = {}
            self.build_configs[project_id][build_config_id] = BuildConfig(build_config_id)
        else:
            if build_config_id not in self.build_configs[project_id]:
                self.build_configs[project_id][build_config_id] = BuildConfig(build_config_id)
        if build_config_type:
            self.build_configs[project_id][build_config_id].build_config_type = build_config_type

    def get_build_config(self, project_id, build_config_id):
        stored_project = self.build_configs.get(project_id)
        if stored_project:
            return stored_project.get(build_config_id, None)

    def set_last_build_id(self, project_id, build_config_id, build_id):
        stored_project = self.build_configs.get(project_id)
        if stored_project and stored_project.get(build_config_id):
            self.build_configs[project_id][build_config_id].last_build_id = build_id

    def get_last_build_id(self, project_id, build_config_id):
        stored_project = self.build_configs.get(project_id)
        if stored_project and stored_project.get(build_config_id):
            build_config = stored_project.get(build_config_id, None)
            if build_config:
                return build_config.last_build_id
        return None
