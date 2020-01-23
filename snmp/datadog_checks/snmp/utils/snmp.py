# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Utilities and helpers related to PySNMP and the SNMP protocol.
"""

import typing

from datadog_checks.base.errors import CheckException

from ..models import SNMPCommandResult, Variable
from ..types import AbstractTransportTarget, CommunityData, ContextData, ObjectType, SnmpEngine, UsmUserData

if typing.TYPE_CHECKING:
    from .config import InstanceConfig


def call_pysnmp_command(
    command,  # type: typing.Callable[..., typing.Generator]
    engine,  # type: SnmpEngine
    auth_data,  # type: typing.Union[CommunityData, UsmUserData]
    transport,  # type: AbstractTransportTarget
    context_data,  # type: ContextData
    *var_binds,  # type: ObjectType
    **options  # type: typing.Any
):
    # type: (...) -> typing.Iterator[SNMPCommandResult]
    results = command(engine, auth_data, transport, context_data, *var_binds, **options)

    # PySNMP returns results as a generator, because:
    #
    # * Some commands yield multiple results, such as GETNEXT or GETBULK.
    # * PySNMP allows running a command multiple times using the `.send()` method
    # of the results generator (but we don't use that feature).
    #
    # The only part we care about is to propagate all yielded results for the one set of
    # arguments that was passed above.
    #
    # Results are presented as tuples of raw values, so we wrap them into class instances that are
    # more convenient to work with.

    for error_indication, error_status, error_index, var_binds in results:
        variables = tuple(Variable(var_bind) for var_bind in var_binds)
        yield SNMPCommandResult(
            variables=variables, error_indication=error_indication, error_status=error_status, error_index=error_index,
        )


def raise_on_error_indication(result, config):
    # type: (SNMPCommandResult, InstanceConfig) -> None
    if result.error_indication:
        message = '{} for instance {}'.format(result.error_indication, config.ip_address)
        raise CheckException(message)
