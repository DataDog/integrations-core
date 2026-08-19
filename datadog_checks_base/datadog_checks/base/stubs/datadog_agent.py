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
        self._sent_reported_issues = defaultdict(list)
        self._sent_resolved_issues = []

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
        self._sent_reported_issues.clear()
        self._sent_resolved_issues.clear()

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

    def assert_reported_issue(self, check_name, issue_id, issue):
        reported = self._sent_reported_issues[check_name]
        matching = [reported_issue for reported_issue in reported if reported_issue['id'] == issue_id]
        assert matching, 'No reported issue with id {} for check {}. Found: {}'.format(issue_id, check_name, reported)
        assert matching[0] == issue, 'Expected reported issue {} for check {}, found {}.'.format(
            issue, check_name, matching[0]
        )

    def assert_resolved_issue(self, issue_id):
        assert issue_id in self._sent_resolved_issues, 'Expected resolved issue {}. Found: {}'.format(
            issue_id, self._sent_resolved_issues
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

    def report_issue(self, check_name, report_json):
        self._sent_reported_issues[check_name].append(json.decode(report_json))

    def resolve_issue(self, issue_id):
        self._sent_resolved_issues.append(issue_id)

    # Prometheus parser stub — uses the Python prometheus_client library
    # to implement the same API that Go exposes in production.

    def __init_parser_state(self):
        if not hasattr(self, '_prometheus_parsers'):
            self._prometheus_parsers = {}
            self._prometheus_parser_counter = 0

    def new_prometheus_parser(self, content_type):
        self.__init_parser_state()
        self._prometheus_parser_counter += 1
        parser_id = self._prometheus_parser_counter
        self._prometheus_parsers[parser_id] = {
            'content_type': content_type,
            'buffer': '',
        }
        return parser_id

    def feed_prometheus_parser(self, parser_id, chunk):
        self.__init_parser_state()
        parser_state = self._prometheus_parsers.get(parser_id)
        if parser_state is None:
            raise ValueError(f'Unknown parser id: {parser_id}')

        buf = parser_state['buffer']
        if buf:
            buf += '\n' + chunk
        else:
            buf = chunk

        # Find the last metric family boundary where a new family starts
        # (a line beginning with '# HELP' or '# TYPE').  Only split there
        # if the text *before* the boundary contains at least one sample
        # line (non-empty, non-comment), otherwise we'd emit an empty
        # parse and lose the actual family.
        lines = buf.split('\n')
        last_boundary = -1
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].startswith('# HELP ') or lines[i].startswith('# TYPE '):
                # Check that there is at least one sample line before this boundary.
                has_sample = any(line and not line.startswith('#') for line in lines[:i])
                if has_sample:
                    last_boundary = i
                break

        if last_boundary <= 0:
            # No complete family yet, buffer everything.
            parser_state['buffer'] = buf
            return ''

        complete = '\n'.join(lines[:last_boundary])
        parser_state['buffer'] = '\n'.join(lines[last_boundary:])

        return self._parse_prometheus_text(complete, parser_state['content_type'])

    def finish_prometheus_parser(self, parser_id):
        self.__init_parser_state()
        parser_state = self._prometheus_parsers.pop(parser_id, None)
        if parser_state is None:
            raise ValueError(f'Unknown parser id: {parser_id}')

        buf = parser_state['buffer']
        if not buf or not buf.strip():
            return ''

        return self._parse_prometheus_text(buf, parser_state['content_type'])

    @staticmethod
    def _is_openmetrics(content_type):
        media_type = content_type.split(';')[0] if content_type else ''
        return media_type == 'application/openmetrics-text'

    @staticmethod
    def _parse_prometheus_text(text, content_type):
        if DatadogAgentStub._is_openmetrics(content_type):
            from prometheus_client.openmetrics.parser import text_fd_to_metric_families

            # OpenMetrics format requires # EOF terminator; strip any existing
            # one and re-add it so intermediate chunks parse correctly.
            lines = [line for line in text.split('\n') if line.strip() != '# EOF']
            lines.append('# EOF')
            text = '\n'.join(lines)
        else:
            from prometheus_client.parser import text_fd_to_metric_families

        families = []
        for metric in text_fd_to_metric_families(iter(text.split('\n'))):
            samples = []
            for s in metric.samples:
                sample = {
                    'name': s.name if hasattr(s, 'name') else s[0],
                    'labels': dict(s.labels if hasattr(s, 'labels') else s[1]),
                    'value': s.value if hasattr(s, 'value') else s[2],
                }
                ts = getattr(s, 'timestamp', None) if hasattr(s, 'timestamp') else None
                if ts is not None:
                    sample['timestamp'] = ts
                exemplar = getattr(s, 'exemplar', None) if hasattr(s, 'exemplar') else None
                if exemplar is not None:
                    sample['exemplar'] = exemplar
                samples.append(sample)
            if samples:
                families.append(
                    {
                        'name': metric.name,
                        'type': metric.type,
                        'help': metric.documentation,
                        'samples': samples,
                    }
                )

        return json.encode(families) if families else ''


# Use the stub as a singleton
datadog_agent = DatadogAgentStub()
