# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Utilities and helpers related to PySNMP and the SNMP protocol.
"""

from typing import TYPE_CHECKING, Any, Callable, Generator, Iterator, Union

from datadog_checks.base.errors import CheckException

from ..models import SNMPCommandResult, Variable
from ..types import AbstractTransportTarget, CommunityData, ContextData, ObjectType, SnmpEngine, UsmUserData

if TYPE_CHECKING:
    from .config import InstanceConfig


def call_pysnmp_command(
    command,  # type: Callable[..., Generator]
    engine,  # type: SnmpEngine
    auth_data,  # type: Union[CommunityData, UsmUserData]
    transport,  # type: AbstractTransportTarget
    context_data,  # type: ContextData
    *var_binds,  # type: ObjectType
    **options  # type: Any
):
    # type: (...) -> Iterator[SNMPCommandResult]
    results = command(engine, auth_data, transport, context_data, *var_binds, **options)

    # PySNMP returns results as a generator, because:
    #
    # * Some commands yield multiple results, such as GETNEXT or GETBULK.
    # * PySNMP allows running a command multiple times using the `.send()` method
    # of the results generator (but we don't use that feature).
    #
    # The only part we care about is to propagate all yielded results for the
    # arguments that were passed above.
    #
    # Results are presented as tuples of raw values, so we wrap them into class instances that are
    # more convenient to work with.

    for error_indication, error_status, error_index, var_binds in results:
        variables = tuple(Variable(var_bind) for var_bind in var_binds)

        # From the SNMP docs: "errorIndex: Non-zero value refers to varBinds[errorIndex-1]".
        # See: http://snmplabs.com/pysnmp/docs/hlapi/asyncore/sync/manager/cmdgen/getcmd.html
        error_variable = variables[error_index - 1] if error_index != 0 else None

        yield SNMPCommandResult(
            variables=variables,
            error_indication=error_indication,
            error_status=error_status,
            error_variable=error_variable,
        )


def raise_on_error_indication(result, config):
    # type: (SNMPCommandResult, InstanceConfig) -> None
    if result.error_indication is not None:
        message = '{} for instance {}'.format(result.error_indication, config.ip_address)
        raise CheckException(message)
