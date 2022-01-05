# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_gauge(check, metric_name, modifiers):
    gauge_method = check.gauge

    def gauge(value, *, tags=None):
        gauge_method(metric_name, value, tags=tags)

    del check
    del modifiers
    return gauge
