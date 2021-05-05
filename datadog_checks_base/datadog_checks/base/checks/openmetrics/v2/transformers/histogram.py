# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ..labels import canonicalize_numeric_label
from ..utils import decumulate_histogram_buckets


def get_histogram(check, metric_name, modifiers, global_options):
    """
    https://prometheus.io/docs/concepts/metric_types/#histogram
    https://github.com/OpenObservability/OpenMetrics/blob/master/specification/OpenMetrics.md#histogram-1
    """
    if global_options['collect_histogram_buckets']:
        if global_options['histogram_buckets_as_distributions']:
            submit_histogram_bucket_method = check.submit_histogram_bucket
            logger = check.log

            def histogram(metric, sample_data, runtime_data):
                for sample, tags, hostname in decumulate_histogram_buckets(sample_data):
                    if not sample.name.endswith('_bucket'):
                        continue

                    lower_bound = canonicalize_numeric_label(sample.labels['lower_bound'])
                    upper_bound = canonicalize_numeric_label(sample.labels['upper_bound'])

                    if lower_bound == upper_bound:
                        # this can happen for -inf/-inf bucket that we don't want to send (always 0)
                        logger.warning(
                            'Metric: %s has bucket boundaries equal, skipping: %s', metric_name, sample.labels
                        )
                        continue

                    submit_histogram_bucket_method(
                        metric_name, sample.value, lower_bound, upper_bound, True, hostname, tags
                    )

        else:
            monotonic_count_method = check.monotonic_count
            bucket_metric = f'{metric_name}.bucket'
            sum_metric = f'{metric_name}.sum'
            count_metric = f'{metric_name}.count'

            if global_options['non_cumulative_histogram_buckets']:

                def histogram(metric, sample_data, runtime_data):
                    has_successfully_executed = runtime_data['has_successfully_executed']

                    for sample, tags, hostname in decumulate_histogram_buckets(sample_data):
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
                        # Skip infinity upper bound as that is otherwise the
                        # same context as the sample suffixed by `_count`
                        elif sample_name.endswith('_bucket') and not sample.labels['upper_bound'].endswith('inf'):
                            monotonic_count_method(
                                bucket_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=has_successfully_executed,
                            )

            # Default behavior
            else:

                def histogram(metric, sample_data, runtime_data):
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
                        # Skip infinity upper bound as that is otherwise the
                        # same context as the sample suffixed by `_count`
                        elif sample_name.endswith('_bucket') and not sample.labels['upper_bound'].endswith('inf'):
                            monotonic_count_method(
                                bucket_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=has_successfully_executed,
                            )

    else:
        monotonic_count_method = check.monotonic_count
        sum_metric = f'{metric_name}.sum'
        count_metric = f'{metric_name}.count'

        def histogram(metric, sample_data, runtime_data):
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

    del check
    del modifiers
    del global_options
    return histogram
