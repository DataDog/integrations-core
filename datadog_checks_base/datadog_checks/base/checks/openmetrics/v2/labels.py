# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ....utils.functions import no_op


class LabelAggregator:
    def __init__(self, check, config):
        share_labels = config.get('share_labels', {})
        if not isinstance(share_labels, dict):
            raise TypeError('Setting `share_labels` must be a mapping')
        elif not share_labels:
            self.populate = no_op
            return

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

    def __call__(self, metrics):
        # TODO: add new option to cache metrics until all configured ones are
        # seen to avoid dependence on the order in which they are exposed
        with self:
            metric_config = self.metric_config.copy()

            for metric in metrics:
                if metric_config and metric.name in metric_config:
                    self.collect(metric, metric_config.pop(metric.name))

                yield metric

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
                for sample in self.allowed_samples(metric, allowed_values):
                    for label, value in sample.labels.items():
                        self.unconditional_labels[label] = value

    def populate(self, labels):
        label_set = frozenset(labels.items())
        labels.update(self.unconditional_labels)

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

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        self.label_sets.clear()
        self.unconditional_labels.clear()


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
