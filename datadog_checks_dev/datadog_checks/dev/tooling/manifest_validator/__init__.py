#  (C) Datadog, Inc. 2021-present
#  All rights reserved
#  Licensed under a 3-clause BSD style license (see LICENSE)
from .v2.validator import get_v2_validators


def get_all_validators(ctx, version_string, is_extras=False, is_marketplace=False):
    return get_v2_validators(ctx, is_extras, is_marketplace)
