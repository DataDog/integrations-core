# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_rate(check, metric_name, modifiers):
    rate_method = check.rate

    def rate(value, *, tags=None):
        rate_method(metric_name, value, tags=tags)

    del check
    del modifiers
    return rate
