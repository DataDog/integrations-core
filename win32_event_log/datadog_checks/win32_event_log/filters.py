# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError

from .constants import EVENT_TYPES


def construct_xpath_query(filters):
    # Here are a bunch of examples of XPath queries:
    # - https://powershell.org/2019/08/a-better-way-to-search-events/
    # - https://www.petri.com/query-xml-event-log-data-using-xpath-in-windows-server-2012-r2
    # - https://blog.backslasher.net/filtering-windows-event-log-using-xpath.html
    if not filters:
        return '*'

    query_parts = []

    # Make sources come first to produce nicer looking queries
    for property_filter, values in sorted(filters.items(), key=lambda item: (item[0] != 'source', item[0])):
        if property_filter not in PROPERTY_CONSTRUCTORS:
            raise ConfigurationError('Unknown property filter: {}'.format(property_filter))
        elif not values:
            raise ConfigurationError('No values set for property filter: {}'.format(property_filter))

        query_parts.append(PROPERTY_CONSTRUCTORS[property_filter](values))

    return '*[System[{}]]'.format(' and '.join(query_parts))


def construct_sources(sources):
    event_sources = set()

    for event_source in sources:
        if not isinstance(event_source, str):
            raise ConfigurationError('Values for event filter `source` must be strings.')

        event_sources.add(event_source)

    parts = ['@Name={}'.format(value_to_xpath_string(value)) for value in sorted(event_sources)]
    return 'Provider[{}]'.format(combine_value_parts(parts))


def construct_types(types):
    event_types = set()

    for event_type in types:
        if not isinstance(event_type, str):
            raise ConfigurationError('Values for event filter `type` must be strings.')

        event_type = event_type.lower()
        if event_type not in EVENT_TYPES:
            raise ConfigurationError('Unknown value for event filter `type`: {}'.format(event_type))

        event_types.add(EVENT_TYPES[event_type])

    parts = ['Level={}'.format(value_to_xpath_string(value)) for value in sorted(event_types)]
    return combine_value_parts(parts)


def construct_ids(ids):
    event_ids = set()

    for event_id in ids:
        if not isinstance(event_id, int):
            raise ConfigurationError('Values for event filter `id` must be integers.')

        event_ids.add(event_id)

    parts = ['EventID={}'.format(value_to_xpath_string(value)) for value in sorted(event_ids)]
    return combine_value_parts(parts)


PROPERTY_CONSTRUCTORS = {'source': construct_sources, 'type': construct_types, 'id': construct_ids}


def value_to_xpath_string(value):
    # Though most sources indicate single quotes are preferred, I cannot find an official directive
    if isinstance(value, str):
        return "'{}'".format(value)

    return str(value)


def combine_value_parts(parts):
    if len(parts) == 1:
        return parts[0]

    return '({})'.format(' or '.join(parts))
