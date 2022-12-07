# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    collection_type = values.get('collection_type')
    if collection_type == 'realtime':
        values['collect_events'] = True
    elif collection_type == 'historical':
        values['collect_events'] = False

    if values.get('collect_events_only', False):
        values['collect_events'] = True

    return values
