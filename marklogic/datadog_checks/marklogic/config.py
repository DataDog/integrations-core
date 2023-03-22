# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from typing import Any, Dict, List, Optional, Pattern  # noqa: F401

from datadog_checks.base import ConfigurationError
from datadog_checks.base.config import _is_affirmative

from .constants import ALLOWED_RESOURCES_FOR_FILTERS


class Config:
    def __init__(self, instance):
        # type: (Dict[str, Any]) -> None
        self.url = instance.get('url', '')  # type: str
        if self.url == '':
            raise ConfigurationError("url is a required configuration.")
        self.tags = instance.get('tags', [])
        self.enable_health_service_checks = _is_affirmative(instance.get('enable_health_service_checks', False))
        self.resource_filters = self.build_resource_filters(instance.get('resource_filters', []))

    @staticmethod
    def build_resource_filters(raw_filters):
        # type: (List[Dict[str, Any]]) -> Dict[str, List[ResourceFilter]]
        created_filters = {'included': [], 'excluded': []}  # type: Dict[str, List[ResourceFilter]]
        for f in raw_filters:
            included = _is_affirmative(f.get('include', True))

            if f.get('pattern') is None or f.get('resource_type') is None:
                raise ConfigurationError('A resource filter requires at least a pattern and a resource_type')
            if f['resource_type'] not in ALLOWED_RESOURCES_FOR_FILTERS:
                raise ConfigurationError('Unknown resource_type: {}'.format(f['resource_type']))

            regex = re.compile(f['pattern'])
            if included:
                created_filters['included'].append(ResourceFilter(f['resource_type'], regex, True, f.get('group')))
            else:
                created_filters['excluded'].append(ResourceFilter(f['resource_type'], regex, False, f.get('group')))

        return created_filters


class ResourceFilter:
    """Represents a given resource filter as defined in the conf.yaml file."""

    def __init__(self, resource_type, regex, is_included=True, group=None):
        # type: (str, Pattern, bool, Optional[str]) -> None
        self.resource_type = resource_type
        self.regex = regex
        self.is_included = is_included
        self.group = group

    def match(self, resource_type, name, group=None):
        # type: (str, str, Optional[str]) -> bool
        if self.resource_type == resource_type and self.regex.match(name) and self.group == group:
            return True
        return False
