# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_counter_gauge(check, metric_name, modifiers, global_options):
    """
    This submits metrics as both a `monotonic_count` suffixed by `.count` and a `gauge` suffixed by `.total`.
    """
    gauge_method = check.gauge
    monotonic_count_method = check.monotonic_count

    total_metric = f'{metric_name}.total'
    count_metric = f'{metric_name}.count'

    def counter_gauge(metric, sample_data, runtime_data):
        flush_first_value = runtime_data['flush_first_value']

        for sample, tags, hostname in sample_data:
            gauge_method(total_metric, sample.value, tags=tags, hostname=hostname)
            monotonic_count_method(
                count_metric,
                sample.value,
                tags=tags,
                hostname=hostname,
                flush_first_value=flush_first_value,
            )

    del check
    del metric_name
    del modifiers
    del global_options
    return counter_gauge
