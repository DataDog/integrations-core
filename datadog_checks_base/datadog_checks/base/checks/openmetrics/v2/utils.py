# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from prometheus_client.samples import Sample


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
                # The first bucket is [-inf, upper_b], but the agent discards buckets with an infinite bound,
                # so keep the lower bound finite: non-negative buckets start at zero, negative ones collapse
                # to a point at upper_b (as the agent already does for the +inf top bucket).
                lower_b = 0 if upper_b >= 0 else upper_b
                bucket_tuples_by_context_upper_bound[context][upper_b] = (
                    lower_b,
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
