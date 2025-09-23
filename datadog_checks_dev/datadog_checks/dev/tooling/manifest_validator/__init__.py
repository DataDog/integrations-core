#  (C) Datadog, Inc. 2021-present
#  All rights reserved
#  Licensed under a 3-clause BSD style license (see LICENSE)
from .common.validator import VersionValidator
from .constants import V2_STRING
from .v2.validator import get_v2_validators


def get_all_validators(ctx, version_string, is_extras=False, is_marketplace=False, ignore_schema=False):
    validators = [VersionValidator()]

    if version_string == V2_STRING:
        validators.extend(get_v2_validators(ctx, is_extras, is_marketplace, ignore_schema))

    return validators
