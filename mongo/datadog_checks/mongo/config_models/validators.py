# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pydantic import ValidationError


def initialize_instance(values, **kwargs):
    if 'hosts' not in values and 'server' not in values:
        raise ValidationError('Hosts is a required field')
    if 'hosts' in values and type(values['hosts']) == str:
        values['hosts'] = [values['hosts']]
    return values
