# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

log = logging.getLogger(__name__)


def collect_all_scalars(key, dictionary):
    if key not in dictionary or dictionary[key] is None:
        yield None, None
    elif isinstance(dictionary[key], dict):
        for tag, _ in dictionary[key].items():
            yield tag, collect_type(tag, dictionary[key], float)
    else:
        yield None, collect_type(key, dictionary, float)


def collect_scalar(key, mapping):
    return collect_type(key, mapping, float)


def collect_string(key, mapping):
    return collect_type(key, mapping, str)


def collect_type(key, mapping, the_type):
    log.debug("Collecting data with %s", key)
    if key not in mapping:
        log.debug("%s returned None", key)
        return None
    log.debug("Collecting done, value %s", mapping[key])
    return the_type(mapping[key])
