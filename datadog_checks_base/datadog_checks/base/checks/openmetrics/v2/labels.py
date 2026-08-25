# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

from datadog_checks.base.utils.functions import no_op


class LabelAggregator:
    def __init__(self, check, config):
        share_labels = config.get('share_labels', {})
        self.target_info = config.get('target_info', False)
        self.target_info_labels = {}

        self._validate_type(share_labels, dict, "Setting `share_labels` must be a mapping")
        self._validate_type(self.target_info, bool, "Setting `target_info` must be a boolean")

        if not share_labels and not self.target_info:
            self.populate = no_op
            return

        self.cache_shared_labels = config.get('cache_shared_labels', True)
        self.shared_labels_cached = False
        self.info_metric = {'target_info': {}}
        self.metric_config = {}
        for metric, config in share_labels.items():
            data = self.metric_config[metric] = {}

            if config is True:
                continue
            elif not isinstance(config, dict):
                raise TypeError(f'Metric `{metric}` of setting `share_labels` must be a mapping or set to `true`')

            if 'values' in config:
                values = config['values']
                if not isinstance(values, list):
                    raise TypeError(f'Option `values` for metric `{metric}` of setting `share_labels` must be an array')

                allowed_values = set()

                for i, value in enumerate(values, 1):
                    value = str(value)

                    try:
                        value = int(value)
                    except Exception:
                        raise TypeError(
                            f'Entry #{i} of option `values` for metric `{metric}` of '
                            f'setting `share_labels` must represent an integer'
                        ) from None
                    else:
                        allowed_values.add(value)

                data['values'] = frozenset(allowed_values)

            for option_name in ('labels', 'match'):
                if option_name not in config:
                    continue

                option = config[option_name]
                if not isinstance(option, list):
                    raise TypeError(
                        f'Option `{option_name}` for metric `{metric}` of setting `share_labels` must be an array'
                    )

                for i, entry in enumerate(option, 1):
                    if not isinstance(entry, str):
                        raise TypeError(
                            f'Entry #{i} of option `{option_name}` for metric `{metric}` '
                            f'of setting `share_labels` must be a string'
                        )

                if option:
                    data[option_name] = frozenset(option)

        self.logger = check.log

        self.label_sets = []

        self.unconditional_labels = {}

    def _validate_type(self, value, expected_type, error_message):
        if not isinstance(value, expected_type):
            raise TypeError(error_message)

    def __call__(self, metrics):
        if self.cache_shared_labels:
            if self.shared_labels_cached:
                yield from metrics
            else:
                metric_config, target_info_metric = self.copy_configs()

                for metric in metrics:
                    self.process_metric(metric, metric_config, target_info_metric)
                    yield metric

                self.shared_labels_cached = True
        else:
            try:
                metric_config, target_info_metric = self.copy_configs()
                cached_metrics = []

                for metric in metrics:
                    self.process_metric(metric, metric_config, target_info_metric)
                    cached_metrics.append(metric)

                    if not (metric_config or target_info_metric):
                        break

                yield from cached_metrics
                yield from metrics
            finally:
                self.label_sets.clear()
                self.unconditional_labels.clear()

    def copy_configs(self):
        return self.metric_config.copy(), self.info_metric.copy()

    def process_metric(self, metric, *configs):
        """
        Collects labels from shared_labels + target_info metrics
        """
        for config in configs:
            if config and metric.name in config:
                self.collect(metric, config.pop(metric.name))

    def process_target_info(self, metric):
        """
        Updates cached target info metrics
        """
        if metric.samples[0].labels != self.target_info_labels:
            self.target_info_labels = metric.samples[0].labels

    def collect(self, metric, config):
        allowed_values = config.get('values')

        if 'match' in config:
            matching_labels = config['match']
            if 'labels' in config:
                labels = config['labels']
                for sample in self.allowed_samples(metric, allowed_values):
                    label_set = set()
                    shared_labels = {}

                    for label, value in sample.labels.items():
                        if label in matching_labels:
                            label_set.add((label, value))

                        if label in labels:
                            shared_labels[label] = value

                    self.label_sets.append((label_set, shared_labels))
            else:
                for sample in self.allowed_samples(metric, allowed_values):
                    label_set = set()
                    shared_labels = {}

                    for label, value in sample.labels.items():
                        if label in matching_labels:
                            label_set.add((label, value))

                        shared_labels[label] = value

                    self.label_sets.append((label_set, shared_labels))
        else:
            if 'labels' in config:
                labels = config['labels']
                for sample in self.allowed_samples(metric, allowed_values):
                    for label, value in sample.labels.items():
                        if label in labels:
                            self.unconditional_labels[label] = value
            else:
                # Store target_info metric labels to be applied to other metrics in payload
                if metric.name == 'target_info':
                    self.target_info_labels.update(
                        {
                            label: value
                            for sample in self.allowed_samples(metric, allowed_values)
                            for label, value in sample.labels.items()
                        }
                    )
                else:
                    # Store shared labels in a seperate attribute
                    self.unconditional_labels.update(
                        {
                            label: value
                            for sample in self.allowed_samples(metric, allowed_values)
                            for label, value in sample.labels.items()
                        }
                    )

    def populate(self, labels):
        label_set = frozenset(labels.items())
        labels.update(ChainMap(self.unconditional_labels, self.target_info_labels))

        for matching_label_set, shared_labels in self.label_sets:
            # Check for subset without incurring the cost of a `.issubset` lookup and call
            if matching_label_set <= label_set:
                labels.update(shared_labels)

    @staticmethod
    def allowed_samples(metric, allowed_values):
        if allowed_values is None:
            for sample in metric.samples:
                yield sample
        else:
            for sample in metric.samples:
                if sample.value in allowed_values:
                    yield sample

    @property
    def configured(self):
        return self.populate is not no_op


def canonicalize_numeric_label(label):
    # Prevent 0.0, see:
    # https://github.com/OpenObservability/OpenMetrics/blob/master/specification/OpenMetrics.md#considerations-canonical-numbers
    return float(label) or 0


def normalize_labels_histogram(labels):
    upper_bound = labels.pop('le', None)
    if upper_bound is not None:
        labels['upper_bound'] = str(canonicalize_numeric_label(upper_bound))


def normalize_labels_summary(labels):
    quantile = labels.get('quantile')
    if quantile is not None:
        labels['quantile'] = str(canonicalize_numeric_label(quantile))


def get_label_normalizer(metric_type):
    if metric_type == 'histogram':
        return normalize_labels_histogram
    elif metric_type == 'summary':
        return normalize_labels_summary
    else:
        return no_op
