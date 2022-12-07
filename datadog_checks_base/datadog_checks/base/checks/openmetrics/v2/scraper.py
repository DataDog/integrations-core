# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import fnmatch
import inspect
import re
from copy import copy, deepcopy
from itertools import chain
from math import isinf, isnan
from typing import List

from prometheus_client.openmetrics.parser import text_fd_to_metric_families as parse_metric_families_strict
from prometheus_client.parser import text_fd_to_metric_families as parse_metric_families

from ....config import is_affirmative
from ....constants import ServiceCheck
from ....errors import ConfigurationError
from ....utils.functions import no_op, return_true
from ....utils.http import RequestsWrapper
from .first_scrape_handler import first_scrape_handler
from .labels import LabelAggregator, get_label_normalizer
from .transform import MetricTransformer

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class OpenMetricsScraper:
    """
    OpenMetricsScraper is a class that can be used to override the default scraping behavior for OpenMetricsBaseCheckV2.

    Minimal example configuration:

    ```yaml
    - openmetrics_endpoint: http://example.com/endpoint
      namespace: "foobar"
      metrics:
      - bar
      - foo
      raw_metric_prefix: "test"
      telemetry: "true"
      hostname_label: node
    ```

    """

    SERVICE_CHECK_HEALTH = 'openmetrics.health'

    def __init__(self, check, config):
        """
        The base class for any scraper overrides.
        """

        self.config = config

        # Save a reference to the check instance
        self.check = check

        # Parse the configuration
        self.endpoint = config['openmetrics_endpoint']

        self.metric_transformer = MetricTransformer(self.check, config)
        self.label_aggregator = LabelAggregator(self.check, config)

        self.enable_telemetry = is_affirmative(config.get('telemetry', False))
        # Make every telemetry submission method a no-op to avoid many lookups of `self.enable_telemetry`
        if not self.enable_telemetry:
            for name, _ in inspect.getmembers(self, predicate=inspect.ismethod):
                if name.startswith('submit_telemetry_'):
                    setattr(self, name, no_op)

        # Prevent overriding an integration's defined namespace
        self.namespace = check.__NAMESPACE__ or config.get('namespace', '')
        if not isinstance(self.namespace, str):
            raise ConfigurationError('Setting `namespace` must be a string')

        self.raw_metric_prefix = config.get('raw_metric_prefix', '')
        if not isinstance(self.raw_metric_prefix, str):
            raise ConfigurationError('Setting `raw_metric_prefix` must be a string')

        self.enable_health_service_check = is_affirmative(config.get('enable_health_service_check', True))

        self.hostname_label = config.get('hostname_label', '')
        if not isinstance(self.hostname_label, str):
            raise ConfigurationError('Setting `hostname_label` must be a string')

        hostname_format = config.get('hostname_format', '')
        if not isinstance(hostname_format, str):
            raise ConfigurationError('Setting `hostname_format` must be a string')

        self.hostname_formatter = None
        if self.hostname_label and hostname_format:
            placeholder = '<HOSTNAME>'
            if placeholder not in hostname_format:
                raise ConfigurationError(f'Setting `hostname_format` does not contain the placeholder `{placeholder}`')

            self.hostname_formatter = lambda hostname: hostname_format.replace('<HOSTNAME>', hostname, 1)

        exclude_labels = config.get('exclude_labels', [])
        if not isinstance(exclude_labels, list):
            raise ConfigurationError('Setting `exclude_labels` must be an array')

        self.exclude_labels = set()
        for i, entry in enumerate(exclude_labels, 1):
            if not isinstance(entry, str):
                raise ConfigurationError(f'Entry #{i} of setting `exclude_labels` must be a string')

            self.exclude_labels.add(entry)

        include_labels = config.get('include_labels', [])
        if not isinstance(include_labels, list):
            raise ConfigurationError('Setting `include_labels` must be an array')
        self.include_labels = set()
        for i, entry in enumerate(include_labels, 1):
            if not isinstance(entry, str):
                raise ConfigurationError(f'Entry #{i} of setting `include_labels` must be a string')
            if entry in self.exclude_labels:
                self.log.debug(
                    'Label `%s` is set in both `exclude_labels` and `include_labels`. Excluding label.', entry
                )
            self.include_labels.add(entry)

        self.rename_labels = config.get('rename_labels', {})
        if not isinstance(self.rename_labels, dict):
            raise ConfigurationError('Setting `rename_labels` must be a mapping')

        for key, value in self.rename_labels.items():
            if not isinstance(value, str):
                raise ConfigurationError(f'Value for label `{key}` of setting `rename_labels` must be a string')

        exclude_metrics = config.get('exclude_metrics', [])
        if not isinstance(exclude_metrics, list):
            raise ConfigurationError('Setting `exclude_metrics` must be an array')

        self.exclude_metrics = set()
        self.exclude_metrics_pattern = None
        exclude_metrics_patterns = []
        for i, entry in enumerate(exclude_metrics, 1):
            if not isinstance(entry, str):
                raise ConfigurationError(f'Entry #{i} of setting `exclude_metrics` must be a string')

            escaped_entry = re.escape(entry)
            if entry == escaped_entry:
                self.exclude_metrics.add(entry)
            else:
                exclude_metrics_patterns.append(entry)

        if exclude_metrics_patterns:
            self.exclude_metrics_pattern = re.compile('|'.join(exclude_metrics_patterns))

        self.exclude_metrics_by_labels = {}
        exclude_metrics_by_labels = config.get('exclude_metrics_by_labels', {})
        if not isinstance(exclude_metrics_by_labels, dict):
            raise ConfigurationError('Setting `exclude_metrics_by_labels` must be a mapping')
        elif exclude_metrics_by_labels:
            for label, values in exclude_metrics_by_labels.items():
                if values is True:
                    self.exclude_metrics_by_labels[label] = return_true
                elif isinstance(values, list):
                    for i, value in enumerate(values, 1):
                        if not isinstance(value, str):
                            raise ConfigurationError(
                                f'Value #{i} for label `{label}` of setting `exclude_metrics_by_labels` '
                                f'must be a string'
                            )

                    self.exclude_metrics_by_labels[label] = (
                        lambda label_value, pattern=re.compile('|'.join(values)): pattern.search(label_value)
                        is not None
                    )
                else:
                    raise ConfigurationError(
                        f'Label `{label}` of setting `exclude_metrics_by_labels` must be an array or set to `true`'
                    )

        custom_tags = config.get('tags', [])  # type: List[str]
        if not isinstance(custom_tags, list):
            raise ConfigurationError('Setting `tags` must be an array')

        for i, entry in enumerate(custom_tags, 1):
            if not isinstance(entry, str):
                raise ConfigurationError(f'Entry #{i} of setting `tags` must be a string')

        # Some tags can be ignored to reduce the cardinality.
        # This can be useful for cost optimization in containerized environments
        # when the openmetrics check is configured to collect custom metrics.
        # Even when the Agent's Tagger is configured to add low-cardinality tags only,
        # some tags can still generate unwanted metric contexts (e.g pod annotations as tags).
        ignore_tags = config.get('ignore_tags', [])
        if ignore_tags:
            ignored_tags_re = re.compile('|'.join(set(ignore_tags)))
            custom_tags = [tag for tag in custom_tags if not ignored_tags_re.search(tag)]

        self.static_tags = copy(custom_tags)
        if is_affirmative(self.config.get('tag_by_endpoint', True)):
            self.static_tags.append(f'endpoint:{self.endpoint}')

        # These will be applied only to service checks
        self.static_tags = tuple(self.static_tags)
        # These will be applied to everything except service checks
        self.tags = self.static_tags

        self.raw_line_filter = None
        raw_line_filters = config.get('raw_line_filters', [])
        if not isinstance(raw_line_filters, list):
            raise ConfigurationError('Setting `raw_line_filters` must be an array')
        elif raw_line_filters:
            for i, entry in enumerate(raw_line_filters, 1):
                if not isinstance(entry, str):
                    raise ConfigurationError(f'Entry #{i} of setting `raw_line_filters` must be a string')

            self.raw_line_filter = re.compile('|'.join(raw_line_filters))

        self.http = RequestsWrapper(config, self.check.init_config, self.check.HTTP_CONFIG_REMAPPER, self.check.log)

        # Decide how strictly we will adhere to the latest version of the specification
        if is_affirmative(config.get('use_latest_spec', False)):
            self.parse_metric_families = parse_metric_families_strict
            # https://github.com/prometheus/client_python/blob/v0.9.0/prometheus_client/openmetrics/exposition.py#L7
            accept_header = 'application/openmetrics-text; version=0.0.1; charset=utf-8'
        else:
            self.parse_metric_families = parse_metric_families
            accept_header = 'text/plain'

        # Request the appropriate exposition format
        if self.http.options['headers'].get('Accept') == '*/*':
            self.http.options['headers']['Accept'] = accept_header

        self.use_process_start_time = is_affirmative(config.get('use_process_start_time'))

        # Used for monotonic counts
        self.flush_first_value = False

    def scrape(self):
        """
        Execute a scrape, and for each metric collected, transform the metric.
        """
        runtime_data = {'flush_first_value': self.flush_first_value, 'static_tags': self.static_tags}

        for metric in self.consume_metrics(runtime_data):
            transformer = self.metric_transformer.get(metric)
            if transformer is None:
                continue

            transformer(metric, self.generate_sample_data(metric), runtime_data)

        self.flush_first_value = True

    def consume_metrics(self, runtime_data):
        """
        Yield the processed metrics and filter out excluded metrics.
        """

        metric_parser = self.parse_metrics()
        if not self.flush_first_value and self.use_process_start_time:
            metric_parser = first_scrape_handler(metric_parser, runtime_data, datadog_agent.get_process_start_time())
        if self.label_aggregator.configured:
            metric_parser = self.label_aggregator(metric_parser)

        for metric in metric_parser:
            if metric.name in self.exclude_metrics or (
                self.exclude_metrics_pattern is not None and self.exclude_metrics_pattern.search(metric.name)
            ):
                self.submit_telemetry_number_of_ignored_metric_samples(metric)
                continue

            yield metric

    def parse_metrics(self):
        """
        Get the line streamer and yield processed metrics.
        """

        line_streamer = self.stream_connection_lines()
        if self.raw_line_filter is not None:
            line_streamer = self.filter_connection_lines(line_streamer)

        for metric in self.parse_metric_families(line_streamer):
            self.submit_telemetry_number_of_total_metric_samples(metric)

            # It is critical that the prefix is removed immediately so that
            # all other configuration may reference the trimmed metric name
            if self.raw_metric_prefix and metric.name.startswith(self.raw_metric_prefix):
                metric.name = metric.name[len(self.raw_metric_prefix) :]

            yield metric

    def generate_sample_data(self, metric):
        """
        Yield a sample of processed data.
        """

        label_normalizer = get_label_normalizer(metric.type)

        for sample in metric.samples:
            value = sample.value
            if isnan(value) or isinf(value):
                self.log.debug('Ignoring sample for metric `%s` as it has an invalid value: %s', metric.name, value)
                continue

            tags = []
            skip_sample = False
            labels = sample.labels
            self.label_aggregator.populate(labels)
            label_normalizer(labels)

            for label_name, label_value in labels.items():
                sample_excluder = self.exclude_metrics_by_labels.get(label_name)
                if sample_excluder is not None and sample_excluder(label_value):
                    skip_sample = True
                    break
                elif label_name in self.exclude_labels:
                    continue
                elif self.include_labels and label_name not in self.include_labels:
                    continue

                label_name = self.rename_labels.get(label_name, label_name)
                tags.append(f'{label_name}:{label_value}')

            if skip_sample:
                continue

            tags.extend(self.tags)

            hostname = ""
            if self.hostname_label and self.hostname_label in labels:
                hostname = labels[self.hostname_label]
                if self.hostname_formatter is not None:
                    hostname = self.hostname_formatter(hostname)

            self.submit_telemetry_number_of_processed_metric_samples()
            yield sample, tags, hostname

    def stream_connection_lines(self):
        """
        Yield the connection line.
        """

        with self.get_connection() as connection:
            for line in connection.iter_lines(decode_unicode=True):
                yield line

    def filter_connection_lines(self, line_streamer):
        """
        Filter connection lines in the line streamer.
        """

        for line in line_streamer:
            if self.raw_line_filter.search(line):
                self.submit_telemetry_number_of_ignored_lines()
            else:
                yield line

    def get_connection(self):
        """
        Send a request to scrape metrics. Return the response or throw an exception.
        """

        try:
            response = self.send_request()
        except Exception as e:
            self.submit_health_check(ServiceCheck.CRITICAL, message=str(e))
            raise
        else:
            try:
                response.raise_for_status()
            except Exception as e:
                self.submit_health_check(ServiceCheck.CRITICAL, message=str(e))
                response.close()
                raise
            else:
                self.submit_health_check(ServiceCheck.OK)

                # Never derive the encoding from the locale
                if response.encoding is None:
                    response.encoding = 'utf-8'

                self.submit_telemetry_endpoint_response_size(response)
                return response

    def send_request(self, **kwargs):
        """
        Send an HTTP GET request to the `openmetrics_endpoint` value.
        """

        kwargs['stream'] = True
        return self.http.get(self.endpoint, **kwargs)

    def set_dynamic_tags(self, *tags):
        """
        Set dynamic tags.
        """

        self.tags = tuple(chain(self.static_tags, tags))

    def submit_health_check(self, status, **kwargs):
        """
        If health service check is enabled, send an `openmetrics.health` service check.
        """

        if self.enable_health_service_check:
            self.service_check(self.SERVICE_CHECK_HEALTH, status, tags=self.static_tags, **kwargs)

    def submit_telemetry_number_of_total_metric_samples(self, metric):
        self.count('telemetry.metrics.input.count', len(metric.samples), tags=self.tags)

    def submit_telemetry_number_of_ignored_metric_samples(self, metric):
        self.count('telemetry.metrics.ignored.count', len(metric.samples), tags=self.tags)

    def submit_telemetry_number_of_processed_metric_samples(self):
        self.count('telemetry.metrics.processed.count', 1, tags=self.tags)

    def submit_telemetry_number_of_ignored_lines(self):
        self.count('telemetry.metrics.blacklist.count', 1, tags=self.tags)

    def submit_telemetry_endpoint_response_size(self, response):
        content_length = response.headers.get('Content-Length')
        if content_length is not None:
            content_length = int(content_length)
        else:
            content_length = len(response.content)

        self.gauge('telemetry.payload.size', content_length, tags=self.tags)

    def __getattr__(self, name):
        # Forward all unknown attribute lookups to the check instance for access to submission methods, hostname, etc.
        attribute = getattr(self.check, name)
        setattr(self, name, attribute)
        return attribute


class OpenMetricsCompatibilityScraper(OpenMetricsScraper):
    """
    This class is designed for existing checks that are transitioning to the new OpenMetrics implementation.
    Checks would use this by overriding the `create_scraper` method like so:

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))
    """

    def __init__(self, check, config):
        new_config = deepcopy(config)
        new_config.setdefault('enable_health_service_check', new_config.pop('health_service_check', True))
        new_config.setdefault('collect_histogram_buckets', new_config.pop('send_histograms_buckets', True))
        new_config.setdefault('non_cumulative_histogram_buckets', new_config.pop('non_cumulative_buckets', False))
        new_config.setdefault('histogram_buckets_as_distributions', new_config.pop('send_distribution_buckets', False))
        new_config.setdefault('raw_metric_prefix', new_config.pop('prometheus_metrics_prefix', ''))
        new_config.setdefault('hostname_label', new_config.pop('label_to_hostname', ''))
        new_config.setdefault('rename_labels', new_config.pop('labels_mapper', {}))
        new_config.setdefault(
            'exclude_metrics', [fnmatch.translate(metric) for metric in new_config.pop('ignore_metrics', [])]
        )

        if 'label_to_hostname_suffix' in new_config:
            suffix = new_config.pop('label_to_hostname_suffix')
            new_config.setdefault('hostname_format', f'<HOSTNAME>{suffix}')

        exclude_metrics_by_labels = new_config.setdefault('exclude_metrics_by_labels', {})
        for metric, labels in new_config.pop('ignore_metrics_by_labels', {}).items():
            if '*' in labels:
                exclude_metrics_by_labels[metric] = True
            else:
                exclude_metrics_by_labels[metric] = labels

        share_labels = new_config.setdefault('share_labels', {})
        for metric, data in new_config.pop('label_joins', {}).items():
            share_labels[metric] = {
                'match': data.get('labels_to_match', []),
                'labels': data.get('labels_to_get', []),
                'values': [1],
            }

        old_metrics = new_config.pop('metrics', [])
        type_overrides = new_config.pop('type_overrides', {})
        metrics = new_config.setdefault('metrics', [])
        for metric in old_metrics:
            data = {}

            if isinstance(metric, str):
                key = fnmatch.translate(metric)
                data[key] = {'name': metric}
                if metric in type_overrides:
                    data[key]['type'] = type_overrides.pop(metric)
            else:
                for name, new_name in metric.items():
                    key = fnmatch.translate(name)
                    data[key] = {'name': new_name}
                    if name in type_overrides:
                        data[key]['type'] = type_overrides.pop(name)

            metrics.append(data)

        for metric, metric_type in type_overrides.items():
            metrics.append({fnmatch.translate(metric): {'type': metric_type}})

        metadata_metric_name = new_config.pop('metadata_metric_name', '')
        metadata_label_map = new_config.pop('metadata_label_map', {})
        if metadata_metric_name and metadata_label_map:
            metadata_name, label_name = metadata_label_map.popitem()
            metrics.append({metadata_metric_name: {'name': metadata_name, 'type': 'metadata', 'label': label_name}})

        bearer_token_auth = new_config.pop('bearer_token_auth', False)
        bearer_token_path = new_config.pop('bearer_token_path', '/var/run/secrets/kubernetes.io/serviceaccount/token')
        if bearer_token_auth:
            new_config.setdefault(
                'auth_token',
                {
                    'reader': {'type': 'file', 'path': bearer_token_path},
                    'writer': {'type': 'header', 'name': 'Authorization', 'value': 'Bearer <TOKEN>'},
                },
            )

        super(OpenMetricsCompatibilityScraper, self).__init__(check, new_config)
