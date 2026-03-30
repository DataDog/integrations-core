# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import weakref
from typing import Any, Dict, Generator  # noqa: F401

import pysnmp.hlapi.v3arch.asyncio as hlapi  # noqa: F401
from pyasn1.type.univ import Null
from pysnmp.entity.rfc3413 import cmdgen
from pysnmp.hlapi.varbinds import CommandGeneratorVarBinds
from pysnmp.proto import errind
from pysnmp.proto.rfc1905 import endOfMibView
from pysnmp.smi.rfc1902 import ObjectIdentity, ObjectType

from datadog_checks.base.errors import CheckException

from .config import InstanceConfig  # noqa: F401

vbProcessor = CommandGeneratorVarBinds()

# pysnmp 7.x make_varbinds/unmake_varbinds expect a Dict cache keyed by engine.
_engine_caches: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _engine_cache(engine):
    # type: (Any) -> Dict[str, Any]
    if engine not in _engine_caches:
        _engine_caches[engine] = {}
    return _engine_caches[engine]


def _handle_error(ctx, config):
    # type: (dict, InstanceConfig) -> None
    error = ctx['error']
    if error:
        message = '{} for device {}'.format(error, config.device)
        raise CheckException(message)


def snmp_get(config, oids, lookup_mib):
    # type: (InstanceConfig, list, bool) -> list
    """Call SNMP GET on a list of oids."""

    if config.device is None:
        raise RuntimeError('No device set')  # pragma: no cover

    def callback(  # type: ignore
        snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBinds, cbCtx
    ):
        newVarBinds = unmakeVarbinds(snmpEngine, varBinds, lookup_mib)

        cbCtx['error'] = errorIndication
        cbCtx['var_binds'] = newVarBinds

    ctx = {}  # type: Dict[str, Any]
    var_binds = vbProcessor.make_varbinds(_engine_cache(config._snmp_engine), oids)

    cmdgen.GetCommandGenerator().send_varbinds(
        config._snmp_engine,
        config.device.target,
        config._context_data.contextEngineId,
        config._context_data.contextName,
        var_binds,
        callback,
        ctx,
    )

    config._snmp_engine.transportDispatcher.runDispatcher()

    _handle_error(ctx, config)

    return ctx['var_binds']


def snmp_getnext(config, oids, lookup_mib, ignore_nonincreasing_oid):
    # type: (InstanceConfig, list, bool, bool) -> Generator
    """Call SNMP GETNEXT on a list of oids. It will iterate on the results if it happens to be under the same prefix."""

    if config.device is None:
        raise RuntimeError('No device set')  # pragma: no cover

    def callback(  # type: ignore
        snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBindTable, cbCtx
    ):
        var_bind_table = [
            vbProcessor.unmake_varbinds(_engine_cache(snmpEngine), row, lookup_mib) for row in varBindTable
        ]
        if ignore_nonincreasing_oid and errorIndication and isinstance(errorIndication, errind.OidNotIncreasing):
            errorIndication = None
        cbCtx['error'] = errorIndication
        cbCtx['var_bind_table'] = var_bind_table[0] if var_bind_table else []

    ctx = {}  # type: Dict[str, Any]

    initial_vars = [x[0] for x in vbProcessor.make_varbinds(_engine_cache(config._snmp_engine), oids)]

    var_binds = oids

    gen = cmdgen.NextCommandGenerator()

    while True:
        gen.send_varbinds(
            config._snmp_engine,
            config.device.target,
            config._context_data.contextEngineId,
            config._context_data.contextName,
            var_binds,
            callback,
            ctx,
        )

        config._snmp_engine.transportDispatcher.runDispatcher()

        _handle_error(ctx, config)

        var_binds = []

        new_initial_vars = []
        for col, var_bind in enumerate(ctx['var_bind_table']):
            name, val = var_bind
            if not isinstance(val, Null) and initial_vars[col].isPrefixOf(name):
                var_binds.append(var_bind)
                new_initial_vars.append(initial_vars[col])
                yield var_bind
        if not var_binds:
            return
        initial_vars = new_initial_vars


def snmp_bulk(config, oid, non_repeaters, max_repetitions, lookup_mib, ignore_nonincreasing_oid):
    # type: (InstanceConfig, hlapi.ObjectType, int, int, bool, bool) -> Generator
    """Call SNMP GETBULK on an oid."""

    if config.device is None:
        raise RuntimeError('No device set')  # pragma: no cover

    def callback(  # type: ignore
        snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBindTable, cbCtx
    ):
        var_bind_table = [
            vbProcessor.unmake_varbinds(_engine_cache(snmpEngine), row, lookup_mib) for row in varBindTable
        ]
        if ignore_nonincreasing_oid and errorIndication and isinstance(errorIndication, errind.OidNotIncreasing):
            errorIndication = None
        cbCtx['error'] = errorIndication
        cbCtx['var_bind_table'] = var_bind_table

    ctx = {}  # type: Dict[str, Any]

    var_binds = [oid]
    initial_var = vbProcessor.make_varbinds(_engine_cache(config._snmp_engine), var_binds)[0][0]

    gen = cmdgen.BulkCommandGenerator()

    while True:
        gen.send_varbinds(
            config._snmp_engine,
            config.device.target,
            config._context_data.contextEngineId,
            config._context_data.contextName,
            non_repeaters,
            max_repetitions,
            vbProcessor.make_varbinds(_engine_cache(config._snmp_engine), var_binds),
            callback,
            ctx,
        )

        config._snmp_engine.transportDispatcher.runDispatcher()

        _handle_error(ctx, config)

        for var_binds in ctx['var_bind_table']:
            name, value = var_binds[0]
            if endOfMibView.isSameTypeWith(value):
                return
            if initial_var.isPrefixOf(name):
                yield var_binds[0]
            else:
                return


def unmakeVarbinds(snmpEngine, varBinds, lookupMib=True):
    """Taken from pysnmp's varbinds.py, amended to not ignore the errors that return when resolving the MIB."""
    if lookupMib:
        mibViewController = vbProcessor.get_mib_view_controller(_engine_cache(snmpEngine))
        varBinds = [
            ObjectType(ObjectIdentity(x[0]), x[1]).resolveWithMib(mibViewController, ignoreErrors=False)
            for x in varBinds
        ]

    return varBinds
