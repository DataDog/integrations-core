# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import math

# Here you can include additional config validators or transformers
#
# def initialize_instance(values, **kwargs):
#     if 'my_option' not in values and 'my_legacy_option' in values:
#         values['my_option'] = values['my_legacy_option']
#     if values.get('my_number') > 10:
#         raise ValueError('my_number max value is 10, got %s' % str(values.get('my_number')))
#
#     return values

INF_SENTINEL = '.inf'


def instance_thresholds(value, **kwargs):
    # Runs on the raw config, before pydantic's lax float parsing would accept strings like
    # 'inf' or '5' that the check reads from the raw instance and can't compare.
    if not isinstance(value, dict):
        return value

    for field in ('warning', 'critical'):
        bounds = value.get(field)
        # `None` falls back to the default range; other non-list shapes are rejected by the model.
        if not isinstance(bounds, (list, tuple)):
            continue

        for position, bound in zip(('lower', 'upper'), bounds):
            _validate_threshold_bound(field, position, bound)

    return value


def _validate_threshold_bound(field, position, bound):
    if bound == INF_SENTINEL:
        if position == 'lower':
            raise ValueError(f"thresholds.{field} lower bound cannot be '{INF_SENTINEL}'")
        return

    if (
        isinstance(bound, bool)
        or not isinstance(bound, (int, float))
        or (isinstance(bound, float) and math.isnan(bound))
    ):
        raise ValueError(
            f"thresholds.{field} {position} bound must be a number or the string '{INF_SENTINEL}', got {bound!r}"
        )
