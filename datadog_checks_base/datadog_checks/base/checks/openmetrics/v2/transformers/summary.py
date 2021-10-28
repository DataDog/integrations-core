# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_summary(check, metric_name, modifiers, global_options):
    """
    https://prometheus.io/docs/concepts/metric_types/#summary
    https://github.com/OpenObservability/OpenMetrics/blob/master/specification/OpenMetrics.md#summary-1
    """
    gauge_method = check.gauge
    monotonic_count_method = check.monotonic_count
    sum_metric = f'{metric_name}.sum'
    count_metric = f'{metric_name}.count'
    quantile_metric = f'{metric_name}.quantile'

    def summary(metric, sample_data, runtime_data):
        has_successfully_executed = runtime_data['has_successfully_executed']

        for sample, tags, hostname in sample_data:
            sample_name = sample.name
            if sample_name.endswith('_sum'):
                monotonic_count_method(
                    sum_metric,
                    sample.value,
                    tags=tags,
                    hostname=hostname,
                    flush_first_value=has_successfully_executed,
                )
            elif sample_name.endswith('_count'):
                monotonic_count_method(
                    count_metric,
                    sample.value,
                    tags=tags,
                    hostname=hostname,
                    flush_first_value=has_successfully_executed,
                )
            elif sample_name == metric.name:
                gauge_method(quantile_metric, sample.value, tags=tags, hostname=hostname)

    del check
    del modifiers
    del global_options
    return summary
