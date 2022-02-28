# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can include additional config validators or transformers
#
def initialize_instance(values, **kwargs):
    errors = []
    queues = values.get('queues')
    if queues is not None:
        queues_set = set(queues)
        if len(queues_set) < len(queues):
            errors.append('`queues` must contain unique values.')

    queue_patterns = values.get('queue_patterns')
    if queue_patterns is not None:
        queue_patterns_set = set(queue_patterns)
        if len(queue_patterns_set) < len(queue_patterns):
            errors.append('`queue_patterns` must contain unique values.')

    queue_regex = values.get('queue_regex')
    if queue_regex is not None:
        queue_regex_set = set(queue_regex)
        if len(queue_regex_set) < len(queue_regex):
            errors.append('`queue_regex` must contain unique values.')

    channels = values.get('channels')
    if channels is not None:
        channels_set = set(channels)
        if len(channels_set) < len(channels):
            errors.append('`channels` must contain unique values.')

    channel_status_mapping = values.get('channel_status_mapping')
    if channel_status_mapping is not None and len(channel_status_mapping) < 1:
        errors.append('`channel_status_mapping` must contain at least 1 mapping.')

    queue_tag_re = values.get('queue_tag_re')
    if queue_tag_re is not None and len(queue_tag_re) < 1:
        errors.append('`queue_tag_re` must contain at least 1 mapping.')

    if len(errors) > 0:
        error_msg = 'Found {} configuration errors: '.format(len(errors))
        for error in errors:
            error_msg += error + ' '
        raise ValueError(error_msg)

    return values
