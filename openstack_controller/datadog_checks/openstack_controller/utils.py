# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

from .exceptions import IncompleteConfig


def get_instance_key(instance):
    i_key = instance.get('name')
    if not i_key:
        # We need a name to identify this instance
        raise IncompleteConfig()
    return i_key
