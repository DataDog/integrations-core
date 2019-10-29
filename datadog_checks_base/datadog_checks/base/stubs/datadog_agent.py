# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class DatadogAgentStub(object):
    def __init__(self):
        self._metadata = {}

    def reset(self):
        self._metadata = {}

    def assert_metadata(self, check_id, data):
        for name, value in data.items():
            assert self._metadata[(check_id, name)] == value

    def assert_metadata_count(self, count):
        assert len(self._metadata) == count

    def get_hostname(self):
        return 'stubbed.hostname'

    def get_config(self, *args, **kwargs):
        return ''

    def get_version(self):
        return '0.0.0'

    def log(*args, **kwargs):
        pass

    def set_check_metadata(self, check_id, name, value):
        self._metadata[(check_id, name)] = value

    def set_external_tags(self, *args, **kwargs):
        pass

    def tracemalloc_enabled(self, *args, **kwargs):
        return False


# Use the stub as a singleton
datadog_agent = DatadogAgentStub()
