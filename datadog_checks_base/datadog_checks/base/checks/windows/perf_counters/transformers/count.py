# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_count(check, metric_name, modifiers):
    count_method = check.count

    def count(value, *, tags=None):
        count_method(metric_name, value, tags=tags)

    del check
    del modifiers
    return count
