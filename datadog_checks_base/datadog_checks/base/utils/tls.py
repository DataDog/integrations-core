# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import ssl
from copy import deepcopy
from typing import TYPE_CHECKING, Any, AnyStr, Dict  # noqa: F401

from ..config import is_affirmative

if TYPE_CHECKING:
    from ..types import InstanceType  # noqa: F401

LOGGER = logging.getLogger(__file__)


# The TLSContextWrapper shares configuration options with the HTTP Request wrapper for simplicity of user configuration.
# To allow for a specific use case where an integraiton needs both a TLSContextWrapper plus the RequestsWrapper but with
# different option, there is the ability to have configuration option with higher priority by using the following
# prefix.
UNIQUE_FIELD_PREFIX = '_tls_context_'

STANDARD_FIELDS = {
    'tls_verify': True,
    'tls_ca_cert': None,
    'tls_cert': None,
    'tls_private_key': None,
    'tls_private_key_password': None,
    'tls_validate_hostname': True,
    'tls_ciphers': 'ALL',
}


class TlsContextWrapper(object):
    __slots__ = ('logger', 'config', 'tls_context')

    def __init__(self, instance, remapper=None, overrides=None):
        default_fields = dict(STANDARD_FIELDS)

        # Override existing config options if there exists any overrides
        instance = deepcopy(instance)

        if overrides:
            for overridden_field, data in overrides.items():
                if instance.get(overridden_field):
                    instance[overridden_field] = data

        # Populate with the default values
        config = {field: instance.get(field, value) for field, value in default_fields.items()}
        for field in STANDARD_FIELDS:
            unique_name = UNIQUE_FIELD_PREFIX + field
            if unique_name in instance:
                config[unique_name] = instance[unique_name]

        if remapper is None:
            remapper = {}

        for remapped_field, data in remapper.items():
            field = data.get('name')

            if field.startswith(UNIQUE_FIELD_PREFIX):
                standard_field_name = field[len(UNIQUE_FIELD_PREFIX) :]
            else:
                standard_field_name = field

            # Ignore fields we don't recognize
            if standard_field_name not in STANDARD_FIELDS:
                continue

            # Ignore remapped fields if the standard one is already used
            if field in instance:
                continue

            # Invert default booleans if need be
            default = default_fields[standard_field_name]
            if data.get('invert'):
                default = not default

            # Get value, with a possible default
            value = instance.get(remapped_field, data.get('default', default))

            # Invert booleans if need be
            if data.get('invert'):
                value = not is_affirmative(value)

            config[field] = value

        if config['tls_ca_cert']:
            config['tls_verify'] = True

        # Populate with the higher-priority configuration options if set
        for field in default_fields:
            unique_name = UNIQUE_FIELD_PREFIX + field
            if unique_name in config:
                config[field] = config[unique_name]
                del config[unique_name]

        self.config = config
        self.tls_context = create_tls_context(self.config)

    def refresh_tls_context(self):
        # type: () -> None
        self.tls_context = create_tls_context(self.config)
