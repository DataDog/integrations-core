# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can include additional config validators or transformers
#
def initialize_instance(values, **kwargs):
    queues = values.get('queues')
    queues_set = set(queues)
    if len(queues) < len(queues_set):
        raise ValueError('`queues` must contain unique values.')
    return values
