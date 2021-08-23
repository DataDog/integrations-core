#  (C) Datadog, Inc. 2021-present
#  All rights reserved
#  Licensed under a 3-clause BSD style license (see LICENSE)

from pkg_resources import packaging

from .v1.validator import get_v1_validators
from .v2.validator import get_v2_validators

v2 = packaging.version.parse("2.0.0")


def get_all_validators(ctx, version, is_extras=False, is_marketplace=False):
    if packaging.version.parse(version) < v2:
        return get_v1_validators(is_extras, is_marketplace)
    elif packaging.version.parse(version) >= v2:
        return get_v2_validators(ctx, is_extras, is_marketplace)
    else:
        # TODO raise error
        return []
