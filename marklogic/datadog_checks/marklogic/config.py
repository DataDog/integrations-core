# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re


class Config:
    def __init__(self, instance):
        self.tags = instance.get('tags', [])
        self.resource_filters = self.build_resource_filters(instance.get('resource_filters', []))

    @staticmethod
    def build_resource_filters(raw_filters):
        return [ResourceFilter(f) for f in raw_filters]


class ResourceFilter:
    def __init__(self, raw_filter):
        # TODO: Validate config
        self.resource = raw_filter['resource']
        self.name = re.compile(raw_filter['name'])
        self.group = raw_filter.get('group')
        self.metric_groups = raw_filter.get('metric_groups')
        self.is_whitelist = raw_filter.get('type') != 'blacklist'
