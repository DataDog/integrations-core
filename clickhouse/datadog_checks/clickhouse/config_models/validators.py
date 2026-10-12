# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def initialize_instance(values, **kwargs):
    if values.get('compression') == '':
        # An empty string historically meant "no compression". Normalize it to None so it
        # validates against the compression enum declared in the spec.
        values['compression'] = None

    return values
