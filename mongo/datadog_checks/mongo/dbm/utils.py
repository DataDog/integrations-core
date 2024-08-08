# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


from datadog_checks.base.utils.common import to_native_string


def format_key_name(formatter, metric_dict: dict) -> dict:
    # convert camelCase to snake_case
    formatted = {}
    for key, value in metric_dict.items():
        formatted_key = to_native_string(formatter(key))
        if formatted_key in metric_dict:
            # If the formatted_key already exists (conflict), use the original key
            formatted_key = key
        if isinstance(value, dict):
            formatted[formatted_key] = format_key_name(formatter, value)
        else:
            formatted[formatted_key] = value
    return formatted
