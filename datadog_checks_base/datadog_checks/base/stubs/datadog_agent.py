# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re
from collections import defaultdict

from datadog_checks.base.utils.format import json


class DatadogAgentStub(object):
    """
    This implements the methods defined by the Agent's
    [C bindings](https://github.com/DataDog/datadog-agent/blob/master/rtloader/common/builtins/datadog_agent.c)
    which in turn call the
    [Go backend](https://github.com/DataDog/datadog-agent/blob/master/pkg/collector/python/datadog_agent.go).

    It also provides utility methods for test assertions.
    """

    def __init__(self):
        self._sent_logs = defaultdict(list)
        self._metadata = {}
        self._cache = {}
        self._config = self.get_default_config()
        self._hostname = 'stubbed.hostname'
        self._process_start_time = 0
        self._external_tags = []
        self._host_tags = "{}"
        self._sent_telemetry = defaultdict(list)

    def get_default_config(self):
        return {'enable_metadata_collection': True}

    def reset(self):
        self._sent_logs.clear()
        self._metadata.clear()
        self._cache.clear()
        self._config = self.get_default_config()
        self._process_start_time = 0
        self._external_tags = []
        self._host_tags = "{}"

    def assert_logs(self, check_id, logs):
        sent_logs = self._sent_logs[check_id]
        assert sent_logs == logs, 'Expected {} logs for check {}, found {}. Submitted logs: {}'.format(
            len(logs), check_id, len(self._sent_logs[check_id]), repr(self._sent_logs)
        )

    def assert_metadata(self, check_id, data):
        actual = {}
        for name in data:
            key = (check_id, name)
            if key in self._metadata:
                actual[name] = self._metadata[key]
        assert data == actual, f'Expected metadata: {data}; actual metadata: {actual}'

    def assert_metadata_count(self, count):
        metadata_items = len(self._metadata)
        assert metadata_items == count, 'Expected {} metadata items, found {}. Submitted metadata: {}'.format(
            count, metadata_items, repr(self._metadata)
        )

    def assert_external_tags(self, hostname, external_tags, match_tags_order=False):
        for h, tags in self._external_tags:
            if h == hostname:
                if not match_tags_order:
                    external_tags = {k: sorted(v) for (k, v) in external_tags.items()}
                    tags = {k: sorted(v) for (k, v) in tags.items()}

                assert external_tags == tags, (
                    'Expected {} external tags for hostname {}, found {}. Submitted external tags: {}'.format(
                        external_tags, hostname, tags, repr(self._external_tags)
                    )
                )
                return

        raise AssertionError('Hostname {} not found in external tags {}'.format(hostname, repr(self._external_tags)))

    def assert_external_tags_count(self, count):
        tags_count = len(self._external_tags)
        assert tags_count == count, 'Expected {} external tags items, found {}. Submitted external tags: {}'.format(
            count, tags_count, repr(self._external_tags)
        )

    def assert_telemetry(self, check_name, metric_name, metric_type, metric_value):
        values = self._sent_telemetry[(check_name, metric_name, metric_type)]
        assert metric_value in values, 'Expected value {} for check {}, metric {}, type {}. Found {}.'.format(
            metric_value, check_name, metric_name, metric_type, values
        )

    def get_hostname(self):
        return self._hostname

    def set_hostname(self, hostname):
        self._hostname = hostname

    def reset_hostname(self):
        self._hostname = 'stubbed.hostname'

    def get_host_tags(self):
        return self._host_tags

    def _set_host_tags(self, tags_dict):
        self._host_tags = json.encode(tags_dict)

    def _reset_host_tags(self):
        self._host_tags = "{}"

    def get_config(self, config_option):
        return self._config.get(config_option, '')

    def get_version(self):
        return '0.0.0'

    def log(self, *args, **kwargs):
        pass

    def set_check_metadata(self, check_id, name, value):
        self._metadata[(check_id, name)] = value

    def send_log(self, log_line, check_id):
        self._sent_logs[check_id].append(json.decode(log_line))

    def set_external_tags(self, external_tags):
        self._external_tags = external_tags

    def tracemalloc_enabled(self, *args, **kwargs):
        return False

    def write_persistent_cache(self, key, value):
        self._cache[key] = value

    def read_persistent_cache(self, key):
        return self._cache.get(key, '')

    def obfuscate_sql(self, query, options=None):
        # Full obfuscation implementation is in go code.
        if options:
            # Options provided is a JSON string because the Go stub requires it, whereas
            # the python stub does not for things such as testing.
            if json.decode(options).get('return_json_metadata', False):
                return json.encode({'query': re.sub(r'\s+', ' ', query or '').strip(), 'metadata': {}})
        return re.sub(r'\s+', ' ', query or '').strip()

    def obfuscate_sql_exec_plan(self, plan, normalize=False):
        # Passthrough stub: obfuscation implementation is in Go code.
        return plan

    def get_process_start_time(self):
        return self._process_start_time

    def set_process_start_time(self, time):
        self._process_start_time = time

    def obfuscate_mongodb_string(self, command):
        # Passthrough stub: obfuscation implementation is in Go code.
        return command

    def emit_agent_telemetry(self, check_name, metric_name, metric_value, metric_type):
        self._sent_telemetry[(check_name, metric_name, metric_type)].append(metric_value)


# Use the stub as a singleton
datadog_agent = DatadogAgentStub()
