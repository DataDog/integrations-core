# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
class Project(object):
    def __init__(self, project_id, build_configs):
        self.project_id = project_id
        self.build_configs = build_configs


class Projects(Project):
    def __init__(self, projects):
        self.projects = projects


class BuildConfig(object):
    def __init__(self, build_config_id, builds):
        self.build_config_id = build_config_id
        self.builds = builds


class BuildConfigs(BuildConfig):
    def __init__(self):
        self.build_configs = {}

    def set_build_config(self, build_type_id):
        if not self.build_configs.get(build_type_id):
            self.build_configs[build_type_id] = {"builds": set()}

    def get_build_config(self, build_type_id):
        if self.build_configs.get(build_type_id):
            return self.build_configs[build_type_id]

    def set_last_build_id(self, build_type_id, build_id, build_number):
        self.build_configs[build_type_id]['last_build_ids'] = {'id': build_id, 'number': build_number}

    def get_last_build_id(self, build_type_id):
        if self.build_configs.get(build_type_id):
            return self.build_configs[build_type_id]["last_build_ids"]
