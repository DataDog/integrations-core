# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict  # noqa: F401

from datadog_checks.base import ConfigurationError, is_affirmative


class SingleStoreConfig(object):
    def __init__(self, instance):
        # type: (Dict[str, Any]) -> None
        if 'host' not in instance:
            raise ConfigurationError("Field 'host' is required to be set to a valid hostname or IP.")
        self.host = str(instance.get('host', ''))
        self.port = int(instance.get('port', 3306))
        self.username = str(instance.get('username', ''))
        self.password = str(instance.get('password', ''))
        self.connect_timeout = int(instance.get('connect_timeout', 10))
        self.read_timeout = int(instance['read_timeout']) if 'read_timeout' in instance else None
        self.tags = instance.get("tags", [])
        if not (isinstance(self.tags, list) and all(isinstance(i, str) for i in self.tags)):
            raise ConfigurationError("Config 'tags' must be a list of strings")
        self.use_tls = is_affirmative(instance.get('use_tls', False))
        self.collect_system_metrics = is_affirmative(instance.get('collect_system_metrics', False))
