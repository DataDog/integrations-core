# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re


class DatadogAgentStub(object):
    """
    This implements the methods defined by the Agent's
    [C bindings](https://github.com/DataDog/datadog-agent/blob/master/rtloader/common/builtins/datadog_agent.c)
    which in turn call the
    [Go backend](https://github.com/DataDog/datadog-agent/blob/master/pkg/collector/python/datadog_agent.go).

    It also provides utility methods for test assertions.
    """

    def __init__(self):
        self._metadata = {}
        self._cache = {}
        self._config = self.get_default_config()

    def get_default_config(self):
        return {'enable_metadata_collection': True}

    def reset(self):
        self._metadata.clear()
        self._cache.clear()
        self._config = self.get_default_config()

    def assert_metadata(self, check_id, data):
        actual = {}
        for name in data:
            key = (check_id, name)
            if key in self._metadata:
                actual[name] = self._metadata[key]
        assert data == actual

    def assert_metadata_count(self, count):
        assert len(self._metadata) == count

    def get_hostname(self):
        return 'stubbed.hostname'

    def get_config(self, config_option):
        return self._config.get(config_option, '')

    def get_version(self):
        return '0.0.0'

    def log(self, *args, **kwargs):
        pass

    def set_check_metadata(self, check_id, name, value):
        self._metadata[(check_id, name)] = value

    def set_external_tags(self, *args, **kwargs):
        pass

    def tracemalloc_enabled(self, *args, **kwargs):
        return False

    def write_persistent_cache(self, key, value):
        self._cache[key] = value

    def read_persistent_cache(self, key):
        return self._cache.get(key, '')

    def obfuscate_sql(self, query):
        # This is only whitespace cleanup, NOT obfuscation. Full obfuscation implementation is in go code.
        return re.sub(r'\s+', ' ', query or '').strip()

    def obfuscate_sql_exec_plan(self, plan, normalize=False):
        # Passthrough stub: obfuscation implementation is in Go code.
        return plan


# Use the stub as a singleton
datadog_agent = DatadogAgentStub()
