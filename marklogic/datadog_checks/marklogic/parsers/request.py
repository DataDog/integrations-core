# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, Generator, List, Tuple  # noqa: F401

from six import iteritems

from .common import build_metric_to_submit, is_metric


def parse_summary_request_base_metrics(data, tags):
    # type: (Dict[str, Any], List[str]) -> Generator[Tuple, None, None]
    return _parse_request_metrics(data, tags)


def parse_per_resource_request_metrics(data, tags):
    # type: (Dict[str, Any], List[str]) -> Generator[Tuple, None, None]
    return _parse_request_metrics(data, tags)


def _parse_request_metrics(data, tags):
    # type: (Dict[str, Any], List[str]) -> Generator[Tuple, None, None]
    list_summary = data['request-default-list']['list-summary']

    for key, value in iteritems(list_summary):
        if is_metric(value):
            metric = build_metric_to_submit("requests.{}".format(key), value, tags)
            if metric is not None:
                yield metric
