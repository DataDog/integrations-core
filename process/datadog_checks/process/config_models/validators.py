# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import math
from typing import Any

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


def instance_thresholds(value: object, **kwargs: Any) -> object:
    # Runs on the raw config, before pydantic's lax float parsing would accept strings like
    # 'inf' or '5' that the check reads from the raw instance and can't compare.
    if not isinstance(value, dict):
        return value

    for field in ('warning', 'critical'):
        bounds = value.get(field)
        # `None` falls back to the default range; other non-list shapes are rejected by the model.
        if not isinstance(bounds, (list, tuple)):
            continue

        # Check every element: the model accepts lists longer than two, and would parse extra
        # strings like 'inf' with the same lax float handling.
        for index, bound in enumerate(bounds):
            _validate_threshold_bound(field, index, bound)

        # Shorter lists are left to the model's `min_length`.
        if len(bounds) >= 2:
            lower, upper = (math.inf if bound == INF_SENTINEL else bound for bound in bounds[:2])
            # Like an infinite lower bound, an inverted range makes every process count a breach.
            if lower > upper:
                raise ValueError(
                    f"thresholds.{field} lower bound cannot exceed the upper bound, got {list(bounds[:2])!r}"
                )

    return value


def _validate_threshold_bound(field: str, index: int, bound: object) -> None:
    if index >= 2:
        # Elements past the two bounds are never read, so neither infinity nor the '.inf'
        # sentinel has a meaning there: hold them to finite numbers. The chained comparison
        # also rejects NaN, and comparing a huge int with a float doesn't overflow.
        if isinstance(bound, bool) or not isinstance(bound, (int, float)) or not -math.inf < bound < math.inf:
            raise ValueError(f"thresholds.{field} bound at index {index} must be a finite number, got {bound!r}")
        return

    label = ('lower bound', 'upper bound')[index]

    if bound != INF_SENTINEL and (
        isinstance(bound, bool)
        or not isinstance(bound, (int, float))
        or (isinstance(bound, float) and math.isnan(bound))
    ):
        raise ValueError(f"thresholds.{field} {label} must be a number or the string '{INF_SENTINEL}', got {bound!r}")

    # A lower bound of `inf` or an upper bound of `-inf` makes every process count a breach.
    # Unquoted YAML `.inf` arrives as a float, so reject that as well as the string. Comparing
    # with `math.inf` rather than calling `math.isinf` keeps a huge int from overflowing.
    if index == 0 and (bound == INF_SENTINEL or bound == math.inf):
        raise ValueError(f"thresholds.{field} lower bound cannot be infinite, got {bound!r}")
    if index == 1 and bound == -math.inf:
        raise ValueError(f"thresholds.{field} upper bound cannot be negative infinity, got {bound!r}")
