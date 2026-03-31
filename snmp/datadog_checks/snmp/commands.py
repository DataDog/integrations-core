# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import weakref
from typing import Any, Dict, Generator  # noqa: F401

import pysnmp.hlapi.v3arch.asyncio as hlapi  # noqa: F401
from pyasn1.error import PyAsn1Error
from pyasn1.type.univ import Null
from pysnmp.entity.rfc3413 import cmdgen
from pysnmp.hlapi.varbinds import CommandGeneratorVarBinds
from pysnmp.proto import errind
from pysnmp.proto.rfc1905 import endOfMibView
from pysnmp.smi.error import SmiError
from pysnmp.smi.rfc1902 import ObjectIdentity, ObjectType
from pysnmp.smi.view import MibViewController

from datadog_checks.base.errors import CheckException

from .config import InstanceConfig  # noqa: F401

vbProcessor = CommandGeneratorVarBinds()

# pysnmp 7.x make_varbinds/unmake_varbinds expect a Dict cache keyed by engine.
_engine_caches: weakref.WeakKeyDictionary = weakref.WeakKeyDictionary()


def _engine_cache(engine):
    # type: (Any) -> Dict[str, Any]
    if engine not in _engine_caches:
        # Pre-populate with a MibViewController backed by the engine's own MibBuilder so that
        # vbProcessor.make_varbinds and the OIDResolver share the same MIB namespace.
        # Without this, MIBs loaded during make_varbinds (e.g. TCP-MIB) are loaded into a
        # separate MibBuilder and are invisible to the resolver when lookup_mib=False.
        cache = {"mibViewController": MibViewController(engine.get_mib_builder())}
        _engine_caches[engine] = cache
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
        try:
            newVarBinds = unmakeVarbinds(snmpEngine, varBinds, lookup_mib)
            cbCtx['error'] = errorIndication
            cbCtx['var_binds'] = newVarBinds
        except Exception as exc:
            cbCtx['error'] = None
            cbCtx['var_binds'] = []
            cbCtx['exception'] = exc
        finally:
            snmpEngine.transport_dispatcher.loop.stop()

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

    config._snmp_engine.transport_dispatcher.run_dispatcher()

    _handle_error(ctx, config)

    if 'exception' in ctx:
        raise ctx['exception']

    return ctx['var_binds']


def snmp_getnext(config, oids, lookup_mib, ignore_nonincreasing_oid):
    # type: (InstanceConfig, list, bool, bool) -> Generator
    """Call SNMP GETNEXT on a list of oids. It will iterate on the results if it happens to be under the same prefix."""

    if config.device is None:
        raise RuntimeError('No device set')  # pragma: no cover

    def callback(  # type: ignore
        snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBindTable, cbCtx
    ):
        try:
            # pysnmp 7.x passes varBindTable as a flat list of (OID, val) pairs
            processed = vbProcessor.unmake_varbinds(_engine_cache(snmpEngine), varBindTable, lookup_mib)
            if ignore_nonincreasing_oid and errorIndication and isinstance(errorIndication, errind.OidNotIncreasing):
                errorIndication = None
            cbCtx['error'] = errorIndication
            cbCtx['var_bind_table'] = processed
        finally:
            snmpEngine.transport_dispatcher.loop.stop()

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

        config._snmp_engine.transport_dispatcher.run_dispatcher()

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
        try:
            # pysnmp 7.x passes varBindTable as a flat list of (OID, val) pairs;
            # wrap each in a list to preserve the expected [(name, val)] row structure.
            unmade = vbProcessor.unmake_varbinds(_engine_cache(snmpEngine), varBindTable, lookup_mib)
            var_bind_table = [[vb] for vb in unmade]
            if ignore_nonincreasing_oid and errorIndication and isinstance(errorIndication, errind.OidNotIncreasing):
                errorIndication = None
            cbCtx['error'] = errorIndication
            cbCtx['var_bind_table'] = var_bind_table
        finally:
            snmpEngine.transport_dispatcher.loop.stop()

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

        config._snmp_engine.transport_dispatcher.run_dispatcher()

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
        resolved = []
        for x in varBinds:
            obj_type = ObjectType(ObjectIdentity(x[0]), x[1]).resolve_with_mib(mibViewController, ignoreErrors=False)
            # pysnmp 7.x bypasses constraint checking for received SimpleAsn1Type values in
            # resolve_with_mib; explicitly validate by cloning through the MIB syntax.
            if not isinstance(obj_type[1], Null):
                mib_node = obj_type[0].get_mib_node()
                if mib_node is not None and hasattr(mib_node, 'getSyntax'):
                    try:
                        mib_node.getSyntax().clone(obj_type[1])
                    except PyAsn1Error as e:
                        raise SmiError(
                            'MIB object %r having type %r failed to cast value %r: %s'
                            % (
                                obj_type[0].prettyPrint(),
                                mib_node.getSyntax().__class__.__name__,
                                obj_type[1],
                                e,
                            )
                        )
            resolved.append(obj_type)
        varBinds = resolved

    return varBinds
