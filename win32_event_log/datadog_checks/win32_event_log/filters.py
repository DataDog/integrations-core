# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base import ConfigurationError

from .constants import EVENT_TYPES_TO_KEYWORD, EVENT_TYPES_TO_LEVEL


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
        if not values:
            raise ConfigurationError('No values set for property filter: {}'.format(property_filter))

        query_parts.append(PROPERTY_CONSTRUCTORS[property_filter](values))

    return '*[System[{}]]'.format(' and '.join(query_parts))


def construct_sources(sources):
    event_sources = set(sources)

    parts = ['@Name={}'.format(value_to_xpath_string(value)) for value in sorted(event_sources)]
    return 'Provider[{}]'.format(combine_value_parts(parts))


def construct_types(types):
    event_levels = set()
    event_keywords = set()

    for event_type in types:
        if event_type in EVENT_TYPES_TO_LEVEL:
            event_levels.add(EVENT_TYPES_TO_LEVEL[event_type])
        elif event_type in EVENT_TYPES_TO_KEYWORD:
            event_keywords.add(EVENT_TYPES_TO_KEYWORD[event_type])
        else:
            raise ConfigurationError('Unknown value for event filter `type`: {}'.format(event_type))

    parts = ['Level={}'.format(value_to_xpath_string(value)) for value in sorted(event_levels)]
    parts.extend('Keywords={}'.format(value_to_xpath_string(value)) for value in sorted(event_keywords))
    return combine_value_parts(parts)


def construct_ids(ids):
    event_ids = set(ids)

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
