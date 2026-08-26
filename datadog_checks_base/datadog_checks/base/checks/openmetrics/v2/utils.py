# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from prometheus_client.samples import Sample

NEGATIVE_INFINITY = float('-inf')


def decumulate_histogram_buckets(sample_data):
    """
    Decumulate buckets in a given histogram metric and adds the lower_bound label (le being upper_bound)
    """
    # TODO: investigate performance optimizations
    new_sample_data = []
    bucket_values_by_context_upper_bound = {}
    for sample, tags, hostname in sample_data:
        if sample.name.endswith('_bucket'):
            context_key = compute_bucket_hash(sample.labels)
            if context_key not in bucket_values_by_context_upper_bound:
                bucket_values_by_context_upper_bound[context_key] = {}
            bucket_values_by_context_upper_bound[context_key][float(sample.labels['upper_bound'])] = sample.value

        new_sample_data.append([sample, tags, hostname])

    sorted_buckets_by_context = {}
    for context in bucket_values_by_context_upper_bound:
        sorted_buckets_by_context[context] = sorted(bucket_values_by_context_upper_bound[context])

    # Tuples (lower_bound, upper_bound, value)
    bucket_tuples_by_context_upper_bound = {}
    for context in sorted_buckets_by_context:
        for i, upper_b in enumerate(sorted_buckets_by_context[context]):
            if i == 0:
                if context not in bucket_tuples_by_context_upper_bound:
                    bucket_tuples_by_context_upper_bound[context] = {}
                if upper_b > 0:
                    # positive buckets start at zero
                    bucket_tuples_by_context_upper_bound[context][upper_b] = (
                        0,
                        upper_b,
                        bucket_values_by_context_upper_bound[context][upper_b],
                    )
                else:
                    # negative buckets start at -inf
                    bucket_tuples_by_context_upper_bound[context][upper_b] = (
                        NEGATIVE_INFINITY,
                        upper_b,
                        bucket_values_by_context_upper_bound[context][upper_b],
                    )
                continue
            tmp = (
                bucket_values_by_context_upper_bound[context][upper_b]
                - bucket_values_by_context_upper_bound[context][sorted_buckets_by_context[context][i - 1]]
            )
            bucket_tuples_by_context_upper_bound[context][upper_b] = (
                sorted_buckets_by_context[context][i - 1],
                upper_b,
                tmp,
            )

    # modify original metric to inject lower_bound & modified value
    for sample, tags, hostname in new_sample_data:
        if not sample.name.endswith('_bucket'):
            yield sample, tags, hostname
        else:
            context_key = compute_bucket_hash(sample.labels)
            matching_bucket_tuple = bucket_tuples_by_context_upper_bound[context_key][
                float(sample.labels['upper_bound'])
            ]

            # Prevent 0.0
            lower_bound = str(matching_bucket_tuple[0] or 0)
            sample.labels['lower_bound'] = lower_bound
            tags.append(f'lower_bound:{lower_bound}')

            yield Sample(sample.name, sample.labels, matching_bucket_tuple[2]), tags, hostname


def compute_bucket_hash(labels):
    # we need the unique context for all the buckets
    # hence we remove the `upper_bound` label
    return hash(frozenset(sorted((k, v) for k, v in labels.items() if k != 'upper_bound')))


def _estimate_percentile(finite_buckets: list[tuple[float, float]], target: float) -> float | None:
    """Linear interpolation within cumulative histogram buckets to estimate a percentile."""
    prev_upper = 0.0
    prev_count = 0.0
    for upper_bound, count in finite_buckets:
        if count >= target:
            if count == prev_count:
                return upper_bound
            fraction = (target - prev_count) / (count - prev_count)
            return prev_upper + fraction * (upper_bound - prev_upper)
        prev_upper = upper_bound
        prev_count = count
    return finite_buckets[-1][0] if finite_buckets else None


def compute_histogram_percentiles(gauge_method, metric_name: str, sample_data: list, percentiles: list) -> None:
    """Compute and submit estimated percentile gauges from raw cumulative histogram bucket data."""
    from math import isinf

    numeric_percentiles = [p for p in percentiles if isinstance(p, (int, float))]
    compute_avg = 'avg' in percentiles

    contexts: dict[int, dict] = {}

    for sample, tags, hostname in sample_data:
        context_key = compute_bucket_hash(sample.labels)
        if context_key not in contexts:
            contexts[context_key] = {'tags': None, 'hostname': hostname, 'buckets': [], 'sum': None, 'count': None}
        ctx = contexts[context_key]

        if sample.name.endswith('_bucket'):
            upper_bound_str = sample.labels.get('upper_bound')
            if upper_bound_str is None:
                continue
            try:
                upper_bound = float(upper_bound_str)
            except ValueError:
                continue
            if ctx['tags'] is None:
                ctx['tags'] = [t for t in tags if not t.startswith('upper_bound:')]
            ctx['buckets'].append((upper_bound, sample.value))
        elif compute_avg and sample.name.endswith('_sum'):
            if ctx['tags'] is None:
                ctx['tags'] = list(tags)
            ctx['sum'] = sample.value
        elif compute_avg and sample.name.endswith('_count'):
            if ctx['tags'] is None:
                ctx['tags'] = list(tags)
            ctx['count'] = sample.value

    for ctx in contexts.values():
        base_tags = ctx['tags'] or []
        hostname = ctx['hostname']
        buckets = ctx['buckets']

        if buckets and numeric_percentiles:
            buckets.sort(key=lambda x: x[0])
            total_count = buckets[-1][1]
            if total_count > 0:
                finite_buckets = [(ub, cnt) for ub, cnt in buckets if not isinf(ub)]
                if finite_buckets:
                    for p in numeric_percentiles:
                        if p == 100:
                            estimate = finite_buckets[-1][0]
                        else:
                            estimate = _estimate_percentile(finite_buckets, p / 100.0 * total_count)
                        if estimate is not None:
                            gauge_method(
                                f'{metric_name}.percentile',
                                estimate,
                                tags=base_tags + [f'percentile:p{p}'],
                                hostname=hostname,
                            )

        if compute_avg and ctx['sum'] is not None and ctx['count']:
            gauge_method(
                f'{metric_name}.percentile',
                ctx['sum'] / ctx['count'],
                tags=base_tags + ['percentile:avg'],
                hostname=hostname,
            )
