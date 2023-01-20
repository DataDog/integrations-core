# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def metric_with_type(name, type):
    return {"name": name, "type": type}


def counter(name):
    return metric_with_type(name, "counter")


def gauge(name):
    return metric_with_type(name, "gauge")
