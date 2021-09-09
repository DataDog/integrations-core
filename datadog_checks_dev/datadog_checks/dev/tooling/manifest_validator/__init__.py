#  (C) Datadog, Inc. 2021-present
#  All rights reserved
#  Licensed under a 3-clause BSD style license (see LICENSE)

from packaging.version import parse

from .constants import V2
from .v1.validator import get_v1_validators
from .v2.validator import get_v2_validators


def get_all_validators(ctx, version_string, is_extras=False, is_marketplace=False):
    if parse(version_string) < V2:
        return get_v1_validators(is_extras, is_marketplace)
    else:
        # e.g. parse(version) >= V2:
        return get_v2_validators(ctx, is_extras, is_marketplace)
