# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

# Here you can include additional config validators or transformers
#


def initialize_instance(values, **kwargs):
    for key, value in values.items():
        if value is None or value == '':
            if key in ['channel', 'queue_manager']:  # These are required options
                raise ValueError("'{}' cannot be empty.".format(key))
            raise ValueError(
                "'{}' cannot be empty. If you don't want to provide a value you can comment this option".format(key)
            )
    return values
