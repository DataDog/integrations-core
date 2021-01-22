# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from six import raise_from

from .....constants import ServiceCheck


def get_service_check(check, metric_name, modifiers, global_options):
    """
    This submits metrics as service checks.

    The required modifier `status_map` is a mapping of values to statuses. Valid statuses include:

    - `OK`
    - `WARNING`
    - `CRITICAL`
    - `UNKNOWN`

    Any encountered values that are not defined will be sent as `UNKNOWN`.
    """
    # Do work in a separate function to avoid having to `del` a bunch of variables
    status_map = compile_service_check_statuses(modifiers)

    service_check_method = check.service_check

    def service_check(metric, sample_data, runtime_data):
        static_tags = runtime_data['static_tags']

        for sample, _, hostname in sample_data:
            service_check_method(
                metric_name,
                status_map.get(int(sample.value), ServiceCheck.UNKNOWN),
                tags=static_tags,
                hostname=hostname,
            )

    del check
    del modifiers
    del global_options
    return service_check


def compile_service_check_statuses(modifiers):
    status_map = modifiers.pop('status_map', None)
    if status_map is None:
        raise ValueError('the `status_map` parameter is required')
    elif not isinstance(status_map, dict):
        raise ValueError('the `status_map` parameter must be a mapping')
    elif not status_map:
        raise ValueError('the `status_map` parameter must not be empty')

    for value, status_string in list(status_map.items()):
        value = str(value)

        try:
            value = int(value)
        except Exception:
            raise_from(TypeError(f'value `{value}` of parameter `status_map` does not represent an integer'), None)

        if not isinstance(status_string, str):
            raise ValueError(f'status `{status_string}` for value `{value}` of parameter `status_map` is not a string')

        status = getattr(ServiceCheck, status_string.upper(), None)
        if status is None:
            raise ValueError(f'invalid status `{status_string}` for value `{value}` of parameter `status_map`')

        status_map[value] = status

    return status_map
