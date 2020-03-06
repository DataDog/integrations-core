# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from typing import Any, Dict, Generator

from pyasn1.type.univ import Null
from pysnmp import hlapi
from pysnmp.entity.rfc3413 import cmdgen
from pysnmp.hlapi.asyncore.cmdgen import vbProcessor
from pysnmp.proto import errind
from pysnmp.proto.rfc1905 import endOfMibView

from datadog_checks.base.errors import CheckException

from .config import InstanceConfig


def _handle_error(ctx, config):
    # type: (dict, InstanceConfig) -> None
    error = ctx['error']
    if error:
        message = '{} for instance {}'.format(error, config.ip_address)
        raise CheckException(message)


def snmp_get(config, oids, lookup_mib):
    # type: (InstanceConfig, list, bool) -> list
    """Call SNMP GET on a list of oids."""

    def callback(snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBinds, cbCtx):
        var_binds = vbProcessor.unmakeVarBinds(snmpEngine, varBinds, lookup_mib)

        cbCtx['error'] = errorIndication
        cbCtx['var_binds'] = var_binds

    ctx = {}  # type: Dict[str, Any]

    var_binds = vbProcessor.makeVarBinds(config._snmp_engine, oids)

    cmdgen.GetCommandGenerator().sendVarBinds(
        config._snmp_engine,
        config._addr_name,
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

    def callback(snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBindTable, cbCtx):
        var_bind_table = [vbProcessor.unmakeVarBinds(snmpEngine, row, lookup_mib) for row in varBindTable]
        if ignore_nonincreasing_oid and errorIndication and isinstance(errorIndication, errind.OidNotIncreasing):
            errorIndication = None
        cbCtx['error'] = errorIndication
        cbCtx['var_bind_table'] = var_bind_table[0]

    ctx = {}  # type: Dict[str, Any]

    initial_vars = [x[0] for x in vbProcessor.makeVarBinds(config._snmp_engine, oids)]

    var_binds = oids

    gen = cmdgen.NextCommandGenerator()

    while True:
        gen.sendVarBinds(
            config._snmp_engine,
            config._addr_name,
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

    def callback(snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBindTable, cbCtx):
        var_bind_table = [vbProcessor.unmakeVarBinds(snmpEngine, row, lookup_mib) for row in varBindTable]
        if ignore_nonincreasing_oid and errorIndication and isinstance(errorIndication, errind.OidNotIncreasing):
            errorIndication = None
        cbCtx['error'] = errorIndication
        cbCtx['var_bind_table'] = var_bind_table

    ctx = {}  # type: Dict[str, Any]

    var_binds = [oid]
    initial_var = vbProcessor.makeVarBinds(config._snmp_engine, var_binds)[0][0]

    gen = cmdgen.BulkCommandGenerator()

    while True:
        gen.sendVarBinds(
            config._snmp_engine,
            config._addr_name,
            config._context_data.contextEngineId,
            config._context_data.contextName,
            non_repeaters,
            max_repetitions,
            vbProcessor.makeVarBinds(config._snmp_engine, var_binds),
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
