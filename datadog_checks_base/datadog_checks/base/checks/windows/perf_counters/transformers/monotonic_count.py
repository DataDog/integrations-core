# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_monotonic_count(check, metric_name, modifiers):
    monotonic_count_method = check.monotonic_count

    def monotonic_count(value, *, tags=None):
        monotonic_count_method(metric_name, value, tags=tags)

    del check
    del modifiers
    return monotonic_count
