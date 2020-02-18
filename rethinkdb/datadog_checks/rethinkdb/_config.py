# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import absolute_import

from typing import Callable, Dict, Iterator, List

import rethinkdb

from datadog_checks.base import ConfigurationError

from ._default_metrics import DEFAULT_METRIC_GROUPS
from ._types import DefaultMetricGroup, Instance, Metric


class Config:
    """
    Hold instance configuration for a RethinkDB check.

    Encapsulates the validation of an `instance` dictionary while improving type information.
    """

    def __init__(self, instance):
        # type: (Instance) -> None
        host = instance.get('host', 'localhost')
        port = instance.get('port', 28015)
        default_metrics = instance.get('default_metrics', True)

        if not isinstance(host, str):
            raise ConfigurationError('host must be a string (got {!r})'.format(type(host)))

        if not isinstance(port, int) or isinstance(port, bool):
            raise ConfigurationError('port must be an integer (got {!r})'.format(type(port)))

        if isinstance(default_metrics, bool):
            default_metrics = {group: default_metrics for group in DEFAULT_METRIC_GROUPS}
        elif isinstance(default_metrics, dict):
            unknown_groups = set(default_metrics) - set(DEFAULT_METRIC_GROUPS)
            if unknown_groups:
                raise ConfigurationError(
                    'default_metrics contains unknown entries: {}'.format(', '.join(unknown_groups))
                )

            invalid_groups = [group for group, enabled in default_metrics.items() if not isinstance(enabled, bool)]
            if invalid_groups:
                raise ConfigurationError(
                    'default_metrics contains entries that are not booleans: {}'.format(', '.join(invalid_groups))
                )
        else:
            raise ConfigurationError(
                'default_metrics must be a boolean or a mapping (got {!r})'.format(type(default_metrics))
            )

        if port < 0:
            raise ConfigurationError('port must be positive (got {!r})'.format(port))

        self.host = host  # type: str
        self.port = port  # type: int
        self.metric_streams = _build_metric_streams(default_metrics)

    def __repr__(self):
        # type: () -> str
        return 'Config(host={host!r}, port={port!r})'.format(host=self.host, port=self.port)


def _build_metric_streams(default_metrics):
    # type: (Dict[DefaultMetricGroup, bool]) -> List[Callable[[rethinkdb.net.Connection], Iterator[Metric]]]
    return [stream for group, stream in DEFAULT_METRIC_GROUPS.items() if default_metrics.get(group, False)]
