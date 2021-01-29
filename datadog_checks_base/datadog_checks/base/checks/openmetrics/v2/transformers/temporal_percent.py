# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .....utils.common import total_time_to_temporal_percent
from .....utils.constants import TIME_UNITS


def get_temporal_percent(check, metric_name, modifiers, global_options):
    """
    This calculates values as a percentage of time since the last check run.

    For example, say the result is a forever increasing counter representing the total time spent pausing for
    garbage collection since start up. That number by itself is quite useless, but as a percentage of time spent
    pausing since the previous collection interval it becomes a useful metric.

    There is one required parameter called `scale` that indicates what unit of time the result should be considered.
    Valid values are:

    - `second`
    - `millisecond`
    - `microsecond`
    - `nanosecond`

    You may also define the unit as an integer number of parts compared to seconds e.g. `millisecond` is
    equivalent to `1000`.
    """
    scale = modifiers.get('scale')
    if scale is None:
        raise ValueError('the `scale` parameter is required')

    if isinstance(scale, str):
        scale = TIME_UNITS.get(scale.lower())
        if scale is None:
            raise ValueError(f"the `scale` parameter must be one of: {' | '.join(sorted(TIME_UNITS))}")
    elif not isinstance(scale, int):
        raise ValueError(
            'the `scale` parameter must be an integer representing parts of a second e.g. 1000 for millisecond'
        )

    rate_method = check.rate

    def temporal_percent(metric, sample_data, runtime_data):
        for sample, tags, hostname in sample_data:
            rate_method(
                metric_name, total_time_to_temporal_percent(sample.value, scale=scale), tags=tags, hostname=hostname
            )

    del check
    del modifiers
    del global_options
    return temporal_percent
