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
        message = '{} for device {}'.format(error, config.device)
        raise CheckException(message)


def snmp_get(config, oids, lookup_mib):
    # type: (InstanceConfig, list, bool) -> list
    """Call SNMP GET on a list of oids."""

    if config.device is None:
        raise RuntimeError('No device set')  # pragma: no cover

    import netsnmp
    print("snmp_get oids", oids)
    varlist = netsnmp.VarList(*[netsnmp.Varbind(".{}".format(o)) for o in oids])

    print("varlist", [o.tag for o in varlist])
    varbinds = config.session.get(varlist)
    print("varlist 1", varlist)
    print("varlist 2", [(o.tag, o.val) for o in varlist])
    print("res varbinds", varbinds)

    return varlist


def snmp_getnext(config, oids, lookup_mib, ignore_nonincreasing_oid):
    # type: (InstanceConfig, list, bool, bool) -> Generator
    """Call SNMP GETNEXT on a list of oids. It will iterate on the results if it happens to be under the same prefix."""

    if config.device is None:
        raise RuntimeError('No device set')  # pragma: no cover

    initial_vars = oids
    # varbinds = oids
    import netsnmp
    varbinds = netsnmp.VarList(*[netsnmp.Varbind(".{}".format(o)) for o in oids])

    while True:
        print('--------------------------')
        print("initial_vars", initial_vars)
        print("varbinds 1", [o.tag for o in varbinds])
        res = config.session.getnext(varbinds)
        print("varbinds 2", [o.tag for o in varbinds])
        print("res", res)

        var_binds = []

        new_initial_vars = []
        print("snmp_getnext varbinds", varbinds)
        for col, item in enumerate(varbinds):
            print("====")
            print("item.tag", item.tag)
            print("item.val", item.val)
            print("item.iid", item.iid)
            print("item", item)
            oid = ".".join([item.tag.lstrip('.'), str(item.iid)])
            initial = initial_vars[col]
            print("oid", oid)
            print("initial", initial)
            if not isinstance(item.val, Null) and oid.startswith(initial):
                var_binds.append(oid)
                new_initial_vars.append(initial)
                yield item
        if not var_binds:
            return
        initial_vars = new_initial_vars
        print("var_binds", var_binds)
        varbinds = netsnmp.VarList(*[netsnmp.Varbind(".{}".format(o)) for o in var_binds])


def snmp_bulk(config, oid, non_repeaters, max_repetitions, lookup_mib, ignore_nonincreasing_oid):
    # type: (InstanceConfig, hlapi.ObjectType, int, int, bool, bool) -> Generator
    """Call SNMP GETBULK on an oid."""

    if config.device is None:
        raise RuntimeError('No device set')  # pragma: no cover

    def callback(  # type: ignore
        snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBindTable, cbCtx
    ):
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
            config.device.target,
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
