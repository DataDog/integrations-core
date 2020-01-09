# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class DatadogAgentStub(object):
    def __init__(self):
        self._metadata = {}

    def reset(self):
        self._metadata.clear()

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

    def get_config(self, *args, **kwargs):
        return ''

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


# Use the stub as a singleton
datadog_agent = DatadogAgentStub()
