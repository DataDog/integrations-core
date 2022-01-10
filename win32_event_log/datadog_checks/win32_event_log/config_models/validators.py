# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    filters = values.setdefault('filters', {})
    if filters:
        if isinstance(filters, dict) and 'type' in filters:
            types = filters['type']
            if isinstance(types, list):
                for i, event_type in enumerate(types):
                    if isinstance(event_type, str):
                        types[i] = event_type.lower()

    if 'bookmark_frequency' not in values:
        # NOTE: Keep this in sync with config spec:
        # instances.payload_size.value.example
        values['bookmark_frequency'] = values.get('payload_size', 10)

    return values


def instance_timeout(value, *, field, **kwargs):
    return int(value * 1000)
