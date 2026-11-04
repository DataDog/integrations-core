{license_header}

# Here you can include additional config validators or transformers.
#
# Constraints on a single option (minimum, maximum, enum, pattern, ...) belong in
# assets/configuration/spec.yaml, not here. Use this file only for rules the spec cannot express.
#
# The `initialize_instance` hook runs before validation, on the raw user input with no defaults applied.
# Use it to rewrite the input, for example to support a legacy option name.
#
# The `check_instance` hook runs after validation, with defaults applied and types coerced.
# Use it for rules that involve several options.
#
# from __future__ import annotations
#
# from typing import TYPE_CHECKING, Any
#
# if TYPE_CHECKING:
#     from .instance import InstanceConfig
#
#
# def initialize_instance(values: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
#     if 'my_option' not in values and 'my_legacy_option' in values:
#         values['my_option'] = values['my_legacy_option']
#
#     return values
#
#
# def check_instance(model: InstanceConfig) -> InstanceConfig:
#     if model.use_tls and not model.tls_ca_cert:
#         raise ValueError('`tls_ca_cert` is required when `use_tls` is enabled')
#
#     return model
