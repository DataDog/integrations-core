# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import math
from functools import partial

from prometheus_client.samples import Sample

from datadog_checks.base.checks.openmetrics.v2.labels import canonicalize_numeric_label
from datadog_checks.base.checks.openmetrics.v2.utils import decumulate_histogram_buckets, remove_bound_tags


def get_histogram(check, metric_name, modifiers, global_options):
    """
    https://prometheus.io/docs/concepts/metric_types/#histogram
    https://github.com/OpenObservability/OpenMetrics/blob/master/specification/OpenMetrics.md#histogram-1
    """
    if global_options['collect_histogram_buckets']:
        if global_options['histogram_buckets_as_distributions']:
            logger = check.log
            omit_histogram_bound_tags = global_options['omit_histogram_bound_tags']
            bound_tag_prefixes = global_options['histogram_bound_tag_prefixes']
            # Pass `multiple_buckets` only when needed, so overrides with the older signature keep working
            submit_histogram_bucket_method = (
                partial(check.submit_histogram_bucket, multiple_buckets=True)
                if omit_histogram_bound_tags
                else check.submit_histogram_bucket
            )

            def submit_bucket(sample: Sample, tags: list[str], hostname: str | None, flush_first_value: bool) -> None:
                lower_bound = canonicalize_numeric_label(sample.labels['lower_bound'])
                upper_bound = canonicalize_numeric_label(sample.labels['upper_bound'])

                if lower_bound == upper_bound and math.isinf(lower_bound):
                    # skip only the degenerate -inf/-inf bucket; finite equal bounds (e.g. le=0) are valid
                    logger.warning('Metric: %s has bucket boundaries equal, skipping: %s', metric_name, sample.labels)
                    return

                if omit_histogram_bound_tags:
                    tags = remove_bound_tags(tags, bound_tag_prefixes)

                submit_histogram_bucket_method(
                    metric_name,
                    sample.value,
                    lower_bound,
                    upper_bound,
                    True,
                    hostname,
                    tags,
                    flush_first_value=flush_first_value,
                )

            if global_options['collect_counters_with_distributions']:
                monotonic_count_method = check.monotonic_count
                sum_metric = f'{metric_name}.sum'
                count_metric = f'{metric_name}.count'

                def histogram(metric, sample_data, runtime_data):
                    flush_first_value = runtime_data['flush_first_value']

                    for sample, tags, hostname in decumulate_histogram_buckets(sample_data):
                        sample_name = sample.name
                        if sample_name.endswith('_sum'):
                            monotonic_count_method(
                                sum_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=flush_first_value,
                            )
                        elif sample_name.endswith('_count'):
                            monotonic_count_method(
                                count_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=flush_first_value,
                            )
                        elif sample_name.endswith('_bucket'):
                            submit_bucket(sample, tags, hostname, flush_first_value)

            else:

                def histogram(metric, sample_data, runtime_data):
                    flush_first_value = runtime_data['flush_first_value']

                    for sample, tags, hostname in decumulate_histogram_buckets(sample_data):
                        if sample.name.endswith('_bucket'):
                            submit_bucket(sample, tags, hostname, flush_first_value)

        else:
            monotonic_count_method = check.monotonic_count
            bucket_metric = f'{metric_name}.bucket'
            sum_metric = f'{metric_name}.sum'
            count_metric = f'{metric_name}.count'

            if global_options['non_cumulative_histogram_buckets']:

                def histogram(metric, sample_data, runtime_data):
                    flush_first_value = runtime_data['flush_first_value']

                    for sample, tags, hostname in decumulate_histogram_buckets(sample_data):
                        sample_name = sample.name
                        if sample_name.endswith('_sum'):
                            monotonic_count_method(
                                sum_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=flush_first_value,
                            )
                        elif sample_name.endswith('_count'):
                            monotonic_count_method(
                                count_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=flush_first_value,
                            )
                        # Skip infinity upper bound as that is otherwise the
                        # same context as the sample suffixed by `_count`
                        elif sample_name.endswith('_bucket') and not sample.labels['upper_bound'].endswith('inf'):
                            monotonic_count_method(
                                bucket_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=flush_first_value,
                            )

            # Default behavior
            else:

                def histogram(metric, sample_data, runtime_data):
                    flush_first_value = runtime_data['flush_first_value']

                    for sample, tags, hostname in sample_data:
                        sample_name = sample.name
                        if sample_name.endswith('_sum'):
                            monotonic_count_method(
                                sum_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=flush_first_value,
                            )
                        elif sample_name.endswith('_count'):
                            monotonic_count_method(
                                count_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=flush_first_value,
                            )
                        # Skip infinity upper bound as that is otherwise the
                        # same context as the sample suffixed by `_count`
                        elif sample_name.endswith('_bucket') and not sample.labels['upper_bound'].endswith('inf'):
                            monotonic_count_method(
                                bucket_metric,
                                sample.value,
                                tags=tags,
                                hostname=hostname,
                                flush_first_value=flush_first_value,
                            )

    else:
        monotonic_count_method = check.monotonic_count
        sum_metric = f'{metric_name}.sum'
        count_metric = f'{metric_name}.count'

        def histogram(metric, sample_data, runtime_data):
            flush_first_value = runtime_data['flush_first_value']

            for sample, tags, hostname in sample_data:
                sample_name = sample.name
                if sample_name.endswith('_sum'):
                    monotonic_count_method(
                        sum_metric,
                        sample.value,
                        tags=tags,
                        hostname=hostname,
                        flush_first_value=flush_first_value,
                    )
                elif sample_name.endswith('_count'):
                    monotonic_count_method(
                        count_metric,
                        sample.value,
                        tags=tags,
                        hostname=hostname,
                        flush_first_value=flush_first_value,
                    )

    del check
    del modifiers
    del global_options
    return histogram
