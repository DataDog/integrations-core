# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from .instance import InstanceConfig


def check_instance(model: InstanceConfig) -> InstanceConfig:
    if model.prefect_userpass is not None:
        if model.username is not None or model.password is not None:
            raise ValueError('`prefect_userpass` cannot be combined with `username` or `password`')
        if cast(str, model.auth_type).lower() != 'basic':
            raise ValueError('`prefect_userpass` requires `auth_type: basic`')

    return model
