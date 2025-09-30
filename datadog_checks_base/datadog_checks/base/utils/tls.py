# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os
import ssl
from copy import deepcopy
from typing import TYPE_CHECKING, Any, AnyStr, Dict, Optional  # noqa: F401

from pydantic import BaseModel

from datadog_checks.base.config import is_affirmative

if TYPE_CHECKING:
    from datadog_checks.base.types import InstanceType  # noqa: F401

LOGGER = logging.getLogger(__file__)


# The TLSContextWrapper shares configuration options with the HTTP Request wrapper for simplicity of user configuration.
# To allow for a specific use case where an integraiton needs both a TLSContextWrapper plus the RequestsWrapper but with
# different option, there is the ability to have configuration option with higher priority by using the following
# prefix.
UNIQUE_FIELD_PREFIX = '_tls_context_'

# https://github.com/python/cpython/blob/ef516d11c1a0f885dba0aba8cf5366502077cdd4/Lib/ssl.py#L158-L165
DEFAULT_PROTOCOL_VERSIONS = ('SSLv3', 'TLSv1.2', 'TLSv1.3')
SUPPORTED_PROTOCOL_VERSIONS = ('SSLv3', 'TLSv1', 'TLSv1.1', 'TLSv1.2', 'TLSv1.3')

STANDARD_FIELDS = {
    'tls_verify': True,
    'tls_ca_cert': None,
    'tls_cert': None,
    'tls_private_key': None,
    'tls_private_key_password': None,
    'tls_validate_hostname': True,
    'tls_ciphers': 'ALL',
}


class TlsConfig(BaseModel, frozen=True):
    """
    Class used internally to cache HTTPS adapters with specific TLS configurations.
    """

    tls_ca_cert: str | bool | None = None
    tls_intermediate_ca_certs: tuple[str, ...] | None = None
    tls_cert: str | None = None
    tls_ciphers: str | tuple[str, ...] = 'ALL'
    tls_use_host_header: bool = False
    tls_ignore_warning: bool = False
    tls_private_key: str | None = None
    tls_private_key_password: str | None = None
    tls_protocols_allowed: tuple[str, ...] = DEFAULT_PROTOCOL_VERSIONS
    tls_validate_hostname: bool = True
    tls_verify: bool = True


def create_ssl_context(config):
    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext
    # https://docs.python.org/3/library/ssl.html#ssl.PROTOCOL_TLS_CLIENT
    context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS)

    LOGGER.debug('Creating SSL context with config: %s', config)
    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.check_hostname
    context.check_hostname = is_affirmative(config['tls_verify']) and config.get('tls_validate_hostname', True)

    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.verify_mode
    context.verify_mode = ssl.CERT_REQUIRED if is_affirmative(config['tls_verify']) else ssl.CERT_NONE

    ciphers = config.get('tls_ciphers', [])
    if isinstance(ciphers, str):
        # If ciphers is a string, assume that it is formatted correctly
        configured_ciphers = "ALL" if "ALL" in ciphers else ciphers
    else:
        configured_ciphers = "ALL" if "ALL" in ciphers else ":".join(ciphers)
    if configured_ciphers:
        LOGGER.debug('Setting TLS ciphers to: %s', configured_ciphers)
        context.set_ciphers(configured_ciphers)

    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_verify_locations
    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_default_certs
    ca_cert = config.get('tls_ca_cert')
    try:
        if ca_cert:
            ca_cert = os.path.expanduser(ca_cert)
            if os.path.isdir(ca_cert):
                context.load_verify_locations(cafile=None, capath=ca_cert, cadata=None)
            else:
                context.load_verify_locations(cafile=ca_cert, capath=None, cadata=None)
        else:
            context.load_default_certs(ssl.Purpose.SERVER_AUTH)
    except FileNotFoundError:
        LOGGER.warning(
            'TLS CA certificate file not found: %s. Please check the `tls_ca_cert` configuration option.',
            ca_cert,
        )
    intermediate_ca_certs = config.get('tls_intermediate_ca_certs')
    try:
        if intermediate_ca_certs:
            context.load_verify_locations(cadata='\n'.join(intermediate_ca_certs))
    except ssl.SSLError:
        LOGGER.warning(
            "TLS intermediate CA certificate(s) could not be loaded: %s. ",
            intermediate_ca_certs,
        )

    # https://docs.python.org/3/library/ssl.html#ssl.SSLContext.load_cert_chain
    client_cert, client_key = config.get('tls_cert'), config.get('tls_private_key')
    client_key_pass = config.get('tls_private_key_password')
    try:
        if client_key:
            client_key = os.path.expanduser(client_key)
        if client_cert:
            client_cert = os.path.expanduser(client_cert)
            context.load_cert_chain(client_cert, keyfile=client_key, password=client_key_pass)
    except FileNotFoundError:
        LOGGER.warning(
            'TLS client certificate file not found: %s. Please check the `tls_cert` configuration option.',
            client_cert,
        )

    return context


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
        self.tls_context = create_ssl_context(self.config)

    def refresh_tls_context(self):
        # type: () -> None
        self.tls_context = create_ssl_context(self.config)
