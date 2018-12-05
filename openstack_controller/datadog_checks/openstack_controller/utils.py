# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from .exceptions import IncompleteConfig


def get_instance_name(instance):
    name = instance.get('name')
    if not name:
        # We need a name to identify this instance
        raise IncompleteConfig()
    return name
