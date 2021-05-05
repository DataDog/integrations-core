# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

import re
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Tuple

from datadog_checks.base.types import ServiceCheckStatus

from ... import is_affirmative
from ...constants import ServiceCheck
from .. import constants
from ..common import compute_percent, total_time_to_temporal_percent
from ..time import ensure_aware_datetime
from .utils import create_extra_transformer

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
    # type: (Dict[str, Callable], str, Any) -> str
    """
    Convert a column to a tag that will be used in every subsequent submission.

    For example, if you named the column `env` and the column returned the value `prod1`, all submissions
    from that row will be tagged by `env:prod1`.

    This also accepts an optional modifier called `boolean` that when set to `true` will transform the result
    to the string `true` or `false`. So for example if you named the column `alive` and the result was the
    number `0` the tag will be `alive:false`.
    """
    template = '{}:{{}}'.format(column_name)
    boolean = is_affirmative(modifiers.pop('boolean', None))

    def tag(_, value, **kwargs):
        if boolean:
            value = str(is_affirmative(value)).lower()

        return template.format(value)

    return tag


def get_tag_list(transformers, column_name, **modifiers):
    # type: (Dict[str, Callable], str, Any) -> Callable[[Any, Any, Any], List[str]]
    """
    Convert a column to a list of tags that will be used in every submission.

    Tag name is determined by `column_name`. The column value represents a list of values. It is expected to be either
    a list of strings, or a comma-separated string.

    For example, if the column is named `server_tag` and the column returned the value `'us,primary'`, then all
    submissions for that row will be tagged by `server_tag:us` and `server_tag:primary`.
    """
    template = '%s:{}' % column_name

    def tag_list(_, value, **kwargs):
        if isinstance(value, str):
            value = [v.strip() for v in value.split(',')]

        return [template.format(v) for v in value]

    return tag_list


def get_monotonic_gauge(transformers, column_name, **modifiers):
    # type: (Dict[str, Callable], str, Any) -> Callable[[Any, Any, Any], None]
    """
    Send the result as both a `gauge` suffixed by `.total` and a `monotonic_count` suffixed by `.count`.
    """
    gauge = transformers['gauge'](transformers, '{}.total'.format(column_name), **modifiers)
    monotonic_count = transformers['monotonic_count'](transformers, '{}.count'.format(column_name), **modifiers)

    def monotonic_gauge(_, value, **kwargs):
        gauge(_, value, **kwargs)
        monotonic_count(_, value, **kwargs)

    return monotonic_gauge


def get_temporal_percent(transformers, column_name, **modifiers):
    # type: (Dict[str, Callable], str, Any) -> Callable[[Any, Any, Any], None]
    """
    Send the result as percentage of time since the last check run as a `rate`.

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
    # type: (Dict[str, Callable], str, Any) -> Callable[[Any, Any, Any], None]
    """
    This is used for querying unstructured data.

    For example, say you want to collect the fields named `foo` and `bar`. Typically, they would be stored like:

    | foo | bar |
    | --- | --- |
    | 4   | 2   |

    and would be queried like:

    ```sql
    SELECT foo, bar FROM ...
    ```

    Often, you will instead find data stored in the following format:

    | metric | value |
    | ------ | ----- |
    | foo    | 4     |
    | bar    | 2     |

    and would be queried like:

    ```sql
    SELECT metric, value FROM ...
    ```

    In this case, the `metric` column stores the name with which to match on and its `value` is
    stored in a separate column.

    The required `items` modifier is a mapping of matched names to column data values. Consider the values
    to be exactly the same as the entries in the `columns` top level field. You must also define a `source`
    modifier either for this transformer itself or in the values of `items` (which will take precedence).
    The source will be treated as the value of the match.

    Say this is your configuration:

    ```yaml
    query: SELECT source1, source2, metric FROM TABLE
    columns:
      - name: value1
        type: source
      - name: value2
        type: source
      - name: metric_name
        type: match
        source: value1
        items:
          foo:
            name: test.foo
            type: gauge
            source: value2
          bar:
            name: test.bar
            type: monotonic_gauge
    ```

    and the result set is:

    | source1 | source2 | metric |
    | ------- | ------- | ------ |
    | 1       | 2       | foo    |
    | 3       | 4       | baz    |
    | 5       | 6       | bar    |

    Here's what would be submitted:

    - `foo` - `test.foo` as a `gauge` with a value of `2`
    - `bar` - `test.bar.total` as a `gauge` and `test.bar.count` as a `monotonic_count`, both with a value of `5`
    - `baz` - nothing since it was not defined as a match item
    """
    # Do work in a separate function to avoid having to `del` a bunch of variables
    compiled_items = _compile_match_items(transformers, modifiers)

    def match(sources, value, **kwargs):
        if value in compiled_items:
            source, transformer = compiled_items[value]
            transformer(sources, sources[source], **kwargs)

    return match


def get_service_check(transformers, column_name, **modifiers):
    # type: (Dict[str, Callable], str, Any) -> Callable[[Any, Any, Any], None]
    """
    Submit a service check.

    The required modifier `status_map` is a mapping of values to statuses. Valid statuses include:

    - `OK`
    - `WARNING`
    - `CRITICAL`
    - `UNKNOWN`

    Any encountered values that are not defined will be sent as `UNKNOWN`.
    """
    # Do work in a separate function to avoid having to `del` a bunch of variables
    status_map = _compile_service_check_statuses(modifiers)

    service_check_method = transformers['__service_check'](transformers, column_name, **modifiers)

    def service_check(_, value, **kwargs):
        service_check_method(_, status_map.get(value, ServiceCheck.UNKNOWN), **kwargs)

    return service_check


def get_time_elapsed(transformers, column_name, **modifiers):
    # type: (Dict[str, Callable], str, Any) -> Callable[[Any, Any, Any], None]
    """
    Send the number of seconds elapsed from a time in the past as a `gauge`.

    For example, if the result is an instance of
    [datetime.datetime](https://docs.python.org/3/library/datetime.html#datetime.datetime) representing 5 seconds ago,
    then this would submit with a value of `5`.

    The optional modifier `format` indicates what format the result is in. By default it is `native`, assuming the
    underlying library provides timestamps as `datetime` objects.

    If the value is a UNIX timestamp you can set the `format` modifier to `unix_time`.

    If the value is a string representation of a date, you must provide the expected timestamp format using the
    [supported codes](https://docs.python.org/3/library/datetime.html#strftime-and-strptime-format-codes).

    Example:

    ```yaml
        columns:
      - name: time_since_x
        type: time_elapsed
        format: native  # default value and can be omitted
      - name: time_since_y
        type: time_elapsed
        format: unix_time
      - name: time_since_z
        type: time_elapsed
        format: "%d/%m/%Y %H:%M:%S"
    ```
    !!! note
        The code `%z` (lower case) is not supported on Windows.
    """
    time_format = modifiers.pop('format', 'native')
    if not isinstance(time_format, str):
        raise ValueError('the `format` parameter must be a string')

    gauge = transformers['gauge'](transformers, column_name, **modifiers)

    if time_format == 'native':

        def time_elapsed(_, value, **kwargs):
            value = ensure_aware_datetime(value)
            gauge(_, (datetime.now(value.tzinfo) - value).total_seconds(), **kwargs)

    elif time_format == 'unix_time':

        def time_elapsed(_, value, **kwargs):
            gauge(_, time.time() - value, **kwargs)

    else:

        def time_elapsed(_, value, **kwargs):
            value = ensure_aware_datetime(datetime.strptime(value, time_format))
            gauge(_, (datetime.now(value.tzinfo) - value).total_seconds(), **kwargs)

    return time_elapsed


def get_expression(transformers, name, **modifiers):
    # type: (Dict[str, Callable], str, Any) -> Callable[[Any, Any, Any], Any]
    """
    This allows the evaluation of a limited subset of Python syntax and built-in functions.

    ```yaml
    columns:
      - name: disk.total
        type: gauge
      - name: disk.used
        type: gauge
    extras:
      - name: disk.free
        expression: disk.total - disk.used
        submit_type: gauge
    ```

    For brevity, if the `expression` attribute exists and `type` does not then it is assumed the type is
    `expression`. The `submit_type` can be any transformer and any extra options are passed down to it.

    The result of every expression is stored, so in lieu of a `submit_type` the above example could also be written as:

    ```yaml
    columns:
      - name: disk.total
        type: gauge
      - name: disk.used
        type: gauge
    extras:
      - name: free
        expression: disk.total - disk.used
      - name: disk.free
        type: gauge
        source: free
    ```

    The order matters though, so for example the following will fail:

    ```yaml
    columns:
      - name: disk.total
        type: gauge
      - name: disk.used
        type: gauge
    extras:
      - name: disk.free
        type: gauge
        source: free
      - name: free
        expression: disk.total - disk.used
    ```

    since the source `free` does not yet exist.
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
    # type: (Dict[str, Callable], str, Any) -> Callable[[Any, Any, Any], None]
    """
    Send a percentage based on 2 sources as a `gauge`.

    The required modifiers are `part` and `total`.

    For example, if you have this configuration:

    ```yaml
    columns:
      - name: disk.total
        type: gauge
      - name: disk.used
        type: gauge
    extras:
      - name: disk.utilized
        type: percent
        part: disk.used
        total: disk.total
    ```

    then the extra metric `disk.utilized` would be sent as a `gauge` calculated as `disk.used / disk.total * 100`.

    If the source of `total` is `0`, then the submitted value will always be sent as `0` too.
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
    'tag_list': get_tag_list,
    'match': get_match,
    'service_check': get_service_check,
    'time_elapsed': get_time_elapsed,
}

EXTRA_TRANSFORMERS = {'expression': get_expression, 'percent': get_percent}


def _compile_service_check_statuses(modifiers):
    # type: (Dict[str, Any]) -> Dict[str, ServiceCheckStatus]
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
    # type: (Dict[str, Any], Dict[str, Any]) -> Dict[str, Tuple[str, Any]]
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


# For documentation generation
class ColumnTransformers(object):
    pass


class ExtraTransformers(object):
    """
    Every column transformer (except `tag`) is supported at this level, the only
    difference being one must set a `source` to retrieve the desired value.

    So for example here:

    ```yaml
    columns:
      - name: foo.bar
        type: rate
    extras:
      - name: foo.current
        type: gauge
        source: foo.bar
    ```

    the metric `foo.current` will be sent as a gauge will the value of `foo.bar`.
    """


# Need a custom object to allow for modification of docstrings
class __TransformerDocumentionHelper(object):
    pass


for name, transformer in sorted(COLUMN_TRANSFORMERS.items()):
    setattr(ColumnTransformers, name, transformer)


for name, transformer in sorted(EXTRA_TRANSFORMERS.items()):
    setattr(ExtraTransformers, name, transformer)
