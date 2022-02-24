# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can include additional config validators or transformers
#
def initialize_instance(values, **kwargs):
    queues = values.get('queues', [])
    queues_set = set(queues)
    if len(queues_set) < len(queues):
        raise ValueError('`queues` must contain unique values.')

    queue_patterns = values.get('queue_patterns', [])
    queue_patterns_set = set(queue_patterns)
    if len(queue_patterns_set) < len(queue_patterns):
        raise ValueError('`queue_patterns` must contain unique values.')

    queue_regex = values.get('queue_regex', [])
    queue_regex_set = set(queue_regex)
    if len(queue_regex_set) < len(queue_regex):
        raise ValueError('`queue_regex` must contain unique values.')

    channels = values.get('channels', [])
    channels_set = set(channels)
    if len(channels_set) < len(channels):
        raise ValueError('`channels` must contain unique values.')

    return values
