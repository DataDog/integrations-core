# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import annotations

from typing import TYPE_CHECKING

from datadog_checks.base import is_affirmative
from datadog_checks.base.utils.containers import iter_unique

from .config_models import InstanceConfig, dict_defaults

CONFIG_MODELS_PACKAGE = 'datadog_checks.ibm_db2.config_models'

if TYPE_CHECKING:
    from .ibm_db2 import IbmDb2Check


def build_config(check: IbmDb2Check) -> InstanceConfig:
    """
    Build the typed instance configuration, folding `global_custom_queries` from `init_config` into
    `custom_queries` according to `use_global_custom_queries`.

    Raises `ConfigurationError` if the instance fails model validation.
    """
    instance = check.instance
    init_config = check.init_config
    args = dict(instance)

    custom_queries = list(instance.get('custom_queries', []))
    use_global_custom_queries = instance.get('use_global_custom_queries', True)
    if use_global_custom_queries == 'extend':
        custom_queries.extend(init_config.get('global_custom_queries', []))
    elif 'global_custom_queries' in init_config and is_affirmative(use_global_custom_queries):
        custom_queries = list(init_config.get('global_custom_queries', []))
    args['custom_queries'] = list(iter_unique(custom_queries))

    # The model defaults `connection_timeout` to 10, but an unset timeout has always meant "use the driver
    # default", so mark it as configured to keep the model from filling it in.
    args.setdefault('connection_timeout', None)

    args['collect_schemas'] = {
        **dict_defaults.instance_collect_schemas().model_dump(),
        **(instance.get('collect_schemas') or {}),
    }

    return check.load_configuration_model(
        CONFIG_MODELS_PACKAGE, 'InstanceConfig', args, check._get_config_model_context(args)
    )
