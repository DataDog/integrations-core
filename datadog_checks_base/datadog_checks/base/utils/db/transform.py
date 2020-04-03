# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import re
from datetime import datetime

from ... import is_affirmative
from ...constants import ServiceCheck
from .. import constants
from ..common import compute_percent, total_time_to_temporal_percent
from .utils import create_extra_transformer, normalize_datetime

# Used for the user-defined `expression`s
ALLOWED_GLOBALS = {
    '__builtins__': {
        # pytest turns it into a dict instead of a module
        name: getattr(__builtins__, name) if hasattr(__builtins__, name) else globals()['__builtins__'][name]
        for name in ('abs', 'all', 'any', 'bool', 'divmod', 'float', 'int', 'len', 'max', 'min', 'pow', 'str', 'sum')
    }
}

# Simple heuristic to not mistake a source for part of a string (which we also transform it into)
SOURCE_PATTERN = r'(?<!"|\')({})(?!"|\')'


def get_tag(transformers, column_name, **modifiers):
    """
    modifiers: boolean
    """
    template = '{}:{{}}'.format(column_name)
    boolean = is_affirmative(modifiers.pop('boolean', None))

    def tag(_, value, **kwargs):
        if boolean:
            value = str(is_affirmative(value)).lower()

        return template.format(value)

    return tag


def get_monotonic_gauge(transformers, column_name, **modifiers):
    gauge = transformers['gauge'](transformers, '{}.total'.format(column_name), **modifiers)
    monotonic_count = transformers['monotonic_count'](transformers, '{}.count'.format(column_name), **modifiers)

    def monotonic_gauge(_, value, **kwargs):
        gauge(_, value, **kwargs)
        monotonic_count(_, value, **kwargs)

    return monotonic_gauge


def get_temporal_percent(transformers, column_name, **modifiers):
    """
    modifiers: scale
    """
    scale = modifiers.pop('scale', None)
    if scale is None:
        raise ValueError('the `scale` parameter is required')

    if isinstance(scale, str):
        scale = constants.TIME_UNITS.get(scale.lower())
        if scale is None:
            raise ValueError(
                'the `scale` parameter must be one of: {}'.format(' | '.join(sorted(constants.TIME_UNITS)))
            )
    elif not isinstance(scale, int):
        raise ValueError(
            'the `scale` parameter must be an integer representing parts of a second e.g. 1000 for millisecond'
        )

    rate = transformers['rate'](transformers, column_name, **modifiers)

    def temporal_percent(_, value, **kwargs):
        rate(_, total_time_to_temporal_percent(float(value), scale=scale), **kwargs)

    return temporal_percent


def get_match(transformers, column_name, **modifiers):
    """
    modifiers: items
    """
    # Do work in a separate function to avoid having to `del` a bunch of variables
    compiled_items = _compile_match_items(transformers, modifiers)

    def match(sources, value, **kwargs):
        if value in compiled_items:
            source, transformer = compiled_items[value]
            transformer(sources, sources[source], **kwargs)

    return match


def get_service_check(transformers, column_name, **modifiers):
    """
    modifiers: status_map
    """
    # Do work in a separate function to avoid having to `del` a bunch of variables
    status_map = _compile_service_check_statuses(modifiers)

    service_check_method = transformers['__service_check'](transformers, column_name, **modifiers)

    def service_check(_, value, **kwargs):
        service_check_method(_, status_map.get(value, ServiceCheck.UNKNOWN), **kwargs)

    return service_check


def get_time_elapsed(transformers, column_name, **modifiers):
    """
    modifiers: format
    """
    time_format = modifiers.pop('format', 'native')
    if not isinstance(time_format, str):
        raise ValueError('the `format` parameter must be a string')

    gauge = transformers['gauge'](transformers, column_name, **modifiers)

    if time_format == 'native':

        def time_elapsed(_, value, **kwargs):
            value = normalize_datetime(value)
            gauge(_, (datetime.now(value.tzinfo) - value).total_seconds(), **kwargs)

    else:

        def time_elapsed(_, value, **kwargs):
            value = normalize_datetime(datetime.strptime(value, time_format))
            gauge(_, (datetime.now(value.tzinfo) - value).total_seconds(), **kwargs)

    return time_elapsed


def get_expression(transformers, name, **modifiers):
    """
    modifiers: expression, verbose, submit_type
    """
    available_sources = modifiers.pop('sources')

    expression = modifiers.pop('expression', None)
    if expression is None:
        raise ValueError('the `expression` parameter is required')
    elif not isinstance(expression, str):
        raise ValueError('the `expression` parameter must be a string')
    elif not expression:
        raise ValueError('the `expression` parameter must not be empty')

    if not modifiers.pop('verbose', False):
        # Sort the sources in reverse order of length to prevent greedy matching
        available_sources = sorted(available_sources, key=lambda s: -len(s))

        # Escape special characters, mostly for the possible dots in metric names
        available_sources = list(map(re.escape, available_sources))

        # Finally, utilize the order by relying on the guarantees provided by the alternation operator
        available_sources = '|'.join(available_sources)

        expression = re.sub(
            SOURCE_PATTERN.format(available_sources),
            # Replace by the particular source that matched
            lambda match_obj: 'SOURCES["{}"]'.format(match_obj.group(1)),
            expression,
        )

    expression = compile(expression, filename=name, mode='eval')

    del available_sources

    if 'submit_type' in modifiers:
        if modifiers['submit_type'] not in transformers:
            raise ValueError('unknown submit_type `{}`'.format(modifiers['submit_type']))

        submit_method = transformers[modifiers.pop('submit_type')](transformers, name, **modifiers)
        submit_method = create_extra_transformer(submit_method)

        def execute_expression(sources, **kwargs):
            result = eval(expression, ALLOWED_GLOBALS, {'SOURCES': sources})
            submit_method(sources, result, **kwargs)
            return result

    else:

        def execute_expression(sources, **kwargs):
            return eval(expression, ALLOWED_GLOBALS, {'SOURCES': sources})

    return execute_expression


def get_percent(transformers, name, **modifiers):
    """
    modifiers: part, total
    """
    available_sources = modifiers.pop('sources')

    part = modifiers.pop('part', None)
    if part is None:
        raise ValueError('the `part` parameter is required')
    elif not isinstance(part, str):
        raise ValueError('the `part` parameter must be a string')
    elif part not in available_sources:
        raise ValueError('the `part` parameter `{}` is not an available source'.format(part))

    total = modifiers.pop('total', None)
    if total is None:
        raise ValueError('the `total` parameter is required')
    elif not isinstance(total, str):
        raise ValueError('the `total` parameter must be a string')
    elif total not in available_sources:
        raise ValueError('the `total` parameter `{}` is not an available source'.format(total))

    del available_sources
    gauge = transformers['gauge'](transformers, name, **modifiers)
    gauge = create_extra_transformer(gauge)

    def percent(sources, **kwargs):
        gauge(sources, compute_percent(sources[part], sources[total]), **kwargs)

    return percent


COLUMN_TRANSFORMERS = {
    'temporal_percent': get_temporal_percent,
    'monotonic_gauge': get_monotonic_gauge,
    'tag': get_tag,
    'match': get_match,
    'service_check': get_service_check,
    'time_elapsed': get_time_elapsed,
}

EXTRA_TRANSFORMERS = {'expression': get_expression, 'percent': get_percent}


def _compile_service_check_statuses(modifiers):
    status_map = modifiers.pop('status_map', None)
    if status_map is None:
        raise ValueError('the `status_map` parameter is required')
    elif not isinstance(status_map, dict):
        raise ValueError('the `status_map` parameter must be a mapping')
    elif not status_map:
        raise ValueError('the `status_map` parameter must not be empty')

    for value, status_string in list(status_map.items()):
        if not isinstance(status_string, str):
            raise ValueError(
                'status `{}` for value `{}` of parameter `status_map` is not a string'.format(status_string, value)
            )

        status = getattr(ServiceCheck, status_string.upper(), None)
        if status is None:
            raise ValueError(
                'invalid status `{}` for value `{}` of parameter `status_map`'.format(status_string, value)
            )

        status_map[value] = status

    return status_map


def _compile_match_items(transformers, modifiers):
    items = modifiers.pop('items', None)
    if items is None:
        raise ValueError('the `items` parameter is required')

    if not isinstance(items, dict):
        raise ValueError('the `items` parameter must be a mapping')

    global_transform_source = modifiers.pop('source', None)

    compiled_items = {}
    for item, data in items.items():
        if not isinstance(data, dict):
            raise ValueError('item `{}` is not a mapping'.format(item))

        transform_name = data.pop('name', None)
        if not transform_name:
            raise ValueError('the `name` parameter for item `{}` is required'.format(item))
        elif not isinstance(transform_name, str):
            raise ValueError('the `name` parameter for item `{}` must be a string'.format(item))

        transform_type = data.pop('type', None)
        if not transform_type:
            raise ValueError('the `type` parameter for item `{}` is required'.format(item))
        elif not isinstance(transform_type, str):
            raise ValueError('the `type` parameter for item `{}` must be a string'.format(item))
        elif transform_type not in transformers:
            raise ValueError('unknown type `{}` for item `{}`'.format(transform_type, item))

        transform_source = data.pop('source', global_transform_source)
        if not transform_source:
            raise ValueError('the `source` parameter for item `{}` is required'.format(item))
        elif not isinstance(transform_source, str):
            raise ValueError('the `source` parameter for item `{}` must be a string'.format(item))

        transform_modifiers = modifiers.copy()
        transform_modifiers.update(data)
        compiled_items[item] = (
            transform_source,
            transformers[transform_type](transformers, transform_name, **transform_modifiers),
        )

    return compiled_items
