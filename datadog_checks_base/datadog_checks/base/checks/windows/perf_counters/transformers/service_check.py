# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .....constants import ServiceCheck
from .....errors import ConfigTypeError, ConfigValueError


def get_service_check(check, metric_name, modifiers):
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

    def service_check(value, *, tags=None):
        service_check_method(
            metric_name,
            status_map.get(int(value), ServiceCheck.UNKNOWN),
            tags=tags,
        )

    del check
    del modifiers
    return service_check


def compile_service_check_statuses(modifiers):
    status_map = modifiers.pop('status_map', None)
    if status_map is None:
        raise ConfigValueError('the `status_map` parameter is required')
    elif not isinstance(status_map, dict):
        raise ConfigTypeError('the `status_map` parameter must be a mapping')
    elif not status_map:
        raise ConfigValueError('the `status_map` parameter must not be empty')

    for value, status_string in list(status_map.items()):
        value = str(value)

        try:
            value = int(value)
        except Exception:
            raise ConfigTypeError(f'value `{value}` of parameter `status_map` does not represent an integer') from None

        if not isinstance(status_string, str):
            raise ConfigTypeError(
                f'status `{status_string}` for value `{value}` of parameter `status_map` is not a string'
            )

        status = getattr(ServiceCheck, status_string.upper(), None)
        if status is None:
            raise ConfigValueError(f'invalid status `{status_string}` for value `{value}` of parameter `status_map`')

        status_map[value] = status

    return status_map
