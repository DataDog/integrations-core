# (C) Datadog, Inc. 2019
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from ... import is_affirmative
from .. import constants
from ..common import total_time_to_temporal_percent


def get_tag(column_name, transformers, **modifiers):
    template = '{}:{{}}'.format(column_name)
    boolean = is_affirmative(modifiers.pop('boolean', None))

    def tag(value, *_, **kwargs):
        if boolean:
            value = str(is_affirmative(value)).lower()

        return template.format(value)

    return tag


def get_monotonic_gauge(column_name, transformers, **modifiers):
    gauge = transformers['gauge']('{}.total'.format(column_name), transformers, **modifiers)
    monotonic_count = transformers['monotonic_count']('{}.count'.format(column_name), transformers, **modifiers)

    def monotonic_gauge(value, *_, **kwargs):
        gauge(value, **kwargs)
        monotonic_count(value, **kwargs)

    return monotonic_gauge


def get_temporal_percent(column_name, transformers, **modifiers):
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

    rate = transformers['rate'](column_name, transformers, **modifiers)

    def temporal_percent(value, *_, **kwargs):
        rate(total_time_to_temporal_percent(value, scale=scale), **kwargs)

    return temporal_percent


def get_match(column_name, transformers, **modifiers):
    # Do work in a separate function to avoid having to `del` a bunch of variables
    compiled_items = _compile_match_items(transformers, modifiers)

    def match(value, row, *_, **kwargs):
        if value in compiled_items:
            source, transformer = compiled_items[value]
            transformer(row[source], **kwargs)

    return match


TRANSFORMERS = {
    'temporal_percent': get_temporal_percent,
    'monotonic_gauge': get_monotonic_gauge,
    'tag': get_tag,
    'match': get_match,
}


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
            transformers[transform_type](transform_name, transformers, **transform_modifiers),
        )

    return compiled_items
