# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pydantic.fields import SHAPE_MAPPING, SHAPE_SEQUENCE, SHAPE_SINGLETON


def get_default_field_value(field, value):
    if field.shape == SHAPE_MAPPING:
        return {}
    elif field.shape == SHAPE_SEQUENCE:
        return []
    elif field.shape == SHAPE_SINGLETON:
        field_type = field.type_
        if field_type in (float, int, str):
            return field_type()

    return value
