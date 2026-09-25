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

    def parse_prometheus_metrics(self, raw_text, content_type):
        from io import StringIO

        from prometheus_client.openmetrics.parser import text_fd_to_metric_families as parse_openmetrics
        from prometheus_client.parser import text_fd_to_metric_families as parse_prometheus

        media_type = content_type.split(';')[0] if content_type else ''
        parse_fn = parse_openmetrics if media_type == 'application/openmetrics-text' else parse_prometheus

        families = []
        for family in parse_fn(StringIO(raw_text)):
            samples = []
            for sample in family.samples:
                labels = dict(sample.labels)
                labels['__name__'] = sample.name
                samples.append({'labels': labels, 'value': sample.value, 'timestamp': sample.timestamp})
            families.append({'name': family.name, 'type': family.type.upper(), 'samples': samples})
        return json.encode(families)

    def process_prometheus_metrics(self, raw_text, config, content_type=''):
        """Parse and process Prometheus/OpenMetrics text with label/tag processing.

        Mirrors the Go ProcessMetricsToJSON function. Returns a JSON-encoded ProcessResult
        object with a 'families' field.

        When share_labels is configured, all source-metric labels are collected from the
        whole payload first (batch mode), then applied to every family regardless of order.
        """
        from io import StringIO
        from math import isinf, isnan

        from prometheus_client.openmetrics.parser import text_fd_to_metric_families as parse_openmetrics
        from prometheus_client.parser import text_fd_to_metric_families as parse_prometheus

        if not raw_text:
            return json.encode({'families': []})

        cfg = json.decode(config)
        media_type = content_type.split(';')[0] if content_type else ''
        parse_fn = parse_openmetrics if media_type == 'application/openmetrics-text' else parse_prometheus

        raw_metric_prefix = cfg.get('raw_metric_prefix', '')
        exclude_metrics = set(cfg.get('exclude_metrics', []))
        exclude_pats = cfg.get('exclude_metrics_patterns', [])
        exclude_re = re.compile('|'.join(exclude_pats)) if exclude_pats else None
        exclude_labels_set = set(cfg.get('exclude_labels', []))
        include_labels_set = set(cfg.get('include_labels', []))
        rename_labels_map = cfg.get('rename_labels', {})
        hostname_label = cfg.get('hostname_label', '')
        hostname_format = cfg.get('hostname_format', '')
        static_tags = list(cfg.get('static_tags', []))
        share_cfg = cfg.get('share_labels', {})

        exclude_by_labels = {}
        for lbl, pats in cfg.get('exclude_metrics_by_labels', {}).items():
            exclude_by_labels[lbl] = re.compile('|'.join(pats)) if pats else None

        # Parse and normalize family names.
        parsed = []
        for fam in parse_fn(StringIO(raw_text)):
            name = fam.name
            ftype = fam.type.upper()
            if ftype == 'COUNTER':
                for sfx in ('_total', '_created'):
                    if name.endswith(sfx):
                        name = name[: -len(sfx)]
                        break
            if raw_metric_prefix and name.startswith(raw_metric_prefix):
                name = name[len(raw_metric_prefix) :]
            parsed.append((name, ftype, fam.samples))

        # Batch mode: collect all source-metric labels from the whole payload first.
        unconditional, conditional = self._collect_shared_labels_batch(parsed, share_cfg)

        result = []
        for name, ftype, samples in parsed:
            if name in exclude_metrics:
                continue
            if exclude_re and exclude_re.search(name):
                continue

            ft_lower = ftype.lower()
            processed_samples = []
            for s in samples:
                if isnan(s.value) or isinf(s.value):
                    continue

                labels = dict(s.labels)
                labels['__name__'] = s.name

                # Apply shared labels (setdefault: existing labels take priority).
                for k, v in unconditional.items():
                    labels.setdefault(k, v)
                for ms, shared in conditional:
                    if ms <= frozenset(labels.items()):
                        for k, v in shared.items():
                            labels.setdefault(k, v)

                # Normalize histogram/summary labels.
                if ft_lower == 'histogram' and 'le' in labels:
                    labels['upper_bound'] = self._canonicalize_numeric(labels.pop('le'))
                elif ft_lower == 'summary' and 'quantile' in labels:
                    labels['quantile'] = self._canonicalize_numeric(labels['quantile'])

                # Check exclude by labels.
                skip = False
                for lbl, pat in exclude_by_labels.items():
                    val = labels.get(lbl)
                    if val is None:
                        continue
                    if pat is None or pat.search(val):
                        skip = True
                        break
                if skip:
                    continue

                # Build tags.
                tags = []
                for lk, lv in labels.items():
                    if lk == '__name__':
                        continue
                    if lk in exclude_labels_set:
                        continue
                    if include_labels_set and lk not in include_labels_set:
                        continue
                    tags.append(f'{rename_labels_map.get(lk, lk)}:{lv}')
                tags.extend(static_tags)

                # Extract hostname.
                hn = ''
                if hostname_label and hostname_label in labels:
                    hn = labels[hostname_label]
                    if hostname_format:
                        hn = hostname_format.replace('<HOSTNAME>', hn, 1)

                sample_name = labels.get('__name__', name)
                out_labels = {k: v for k, v in labels.items() if k != '__name__'}
                processed_samples.append({
                    'sample_name': sample_name,
                    'value': s.value,
                    'tags': tags,
                    'hostname': hn,
                    'labels': out_labels,
                })

            if processed_samples:
                result.append({'name': name, 'type': ftype, 'samples': processed_samples})

        return json.encode({'families': result})

    @staticmethod
    def _collect_shared_labels_batch(parsed, share_cfg):
        """Collect all shared labels from source metrics in a single batch pass."""
        unconditional: dict = {}
        conditional: list = []
        for name, _ftype, samples in parsed:
            sl = share_cfg.get(name)
            if sl is None:
                continue
            match_keys = set(sl.get('match', []))
            label_keys = set(sl.get('labels', []))
            all_labels = not label_keys
            allowed_vals = {float(v) for v in sl.get('values', [])}
            any_val = not allowed_vals
            for s in samples:
                if not any_val and s.value not in allowed_vals:
                    continue
                if match_keys:
                    ms = frozenset((k, v) for k, v in s.labels.items() if k in match_keys)
                    shared = {k: v for k, v in s.labels.items() if all_labels or k in label_keys}
                    conditional.append((ms, shared))
                else:
                    for k, v in s.labels.items():
                        if all_labels or k in label_keys:
                            unconditional[k] = v
        return unconditional, conditional

    @staticmethod
    def _canonicalize_numeric(s):
        """Match Python's canonicalize_numeric_label: str(float(label) or 0)."""
        try:
            f = float(s)
            return str(f or 0)
        except (ValueError, OverflowError):
            return s


# Use the stub as a singleton
datadog_agent = DatadogAgentStub()
