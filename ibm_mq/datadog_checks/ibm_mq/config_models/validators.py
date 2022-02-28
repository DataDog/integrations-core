# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    errors = []

    unique_items_options = ['queues', 'queue_patterns', 'queue_regex', 'channels']
    for unique_opt in unique_items_options:
        value = values.get(unique_opt)
        if value is not None:
            value_set = set(value)
            if len(value_set) < len(value):
                errors.append('`{}` must contain unique values.'.format(unique_opt))

    min_props_options = ['channel_status_mapping', 'queue_tag_re']
    for min_prop_opt in min_props_options:
        value = values.get(min_prop_opt)
        if value is not None and len(value) < 1:
            errors.append('`{}` must contain at least 1 mapping.'.format(min_prop_opt))

    if len(errors) > 0:
        error_msg = 'Found {} configuration errors: '.format(len(errors))
        for error in errors:
            error_msg += error + ' '
        raise ValueError(error_msg)

    return values
