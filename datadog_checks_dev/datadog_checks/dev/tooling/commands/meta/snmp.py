# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os

import click
import yaml

from ..console import CONTEXT_SETTINGS


@click.group(context_settings=CONTEXT_SETTINGS, short_help='SNMP utilities')
def snmp():
    pass


def fetch_mib(mib):
    import pysnmp_mibs
    from pysmi.codegen import PySnmpCodeGen
    from pysmi.compiler import MibCompiler
    from pysmi.parser import SmiStarParser
    from pysmi.reader import HttpReader
    from pysmi.writer import PyFileWriter

    target_directory = os.path.dirname(pysnmp_mibs.__file__)

    reader = HttpReader('mibs.snmplabs.com', 80, '/asn1/@mib@')
    mibCompiler = MibCompiler(SmiStarParser(), PySnmpCodeGen(), PyFileWriter(target_directory))

    mibCompiler.addSources(reader)

    mibCompiler.compile(mib)


@snmp.command(context_settings=CONTEXT_SETTINGS, short_help='Translate MIB name to OIDs in SNMP profiles')
@click.argument('profile_path')
@click.pass_context
def translate_profile(ctx, profile_path):
    """
    Do OID translation in a SNMP profile. This isn't a plain replacement, as it
    doesn't preserve comments and indent, but it should automate most of the
    work.

    You'll need to install pysnmp and pysnmp-mibs manually beforehand.
    """
    # Leave imports in function to not add the dependencies
    from pysnmp import hlapi
    from pysnmp.smi import view
    from pysnmp.smi.error import MibNotFoundError

    snmp_engine = hlapi.SnmpEngine()
    mib_builder = snmp_engine.getMibBuilder()

    mib_view_controller = view.MibViewController(mib_builder)

    with open(profile_path) as f:
        data = yaml.safe_load(f.read())

    output = []
    for metric in data['metrics']:
        mib = metric['MIB']
        try:
            mib_view_controller.mibBuilder.loadModule(mib)
        except MibNotFoundError:
            fetch_mib(mib)
        if 'table' in metric:
            table = metric['table']
            node = mib_view_controller.mibBuilder.importSymbols(mib, table)[0]
            value = '.'.join([str(i) for i in node.getName()])
            table = {'name': table, 'OID': value}
            symbols = []
            for symbol in metric['symbols']:
                node = mib_view_controller.mibBuilder.importSymbols(mib, symbol)[0]
                value = '.'.join([str(i) for i in node.getName()])
                symbols.append({'name': symbol, 'OID': value})
            tags = []
            for tag in metric['metric_tags']:
                if 'column' in tag:
                    tag_mib = tag.get('MIB', mib)
                    key = tag['column']
                    node = mib_view_controller.mibBuilder.importSymbols(tag_mib, key)[0]
                    value = '.'.join([str(i) for i in node.getName()])
                    tag = tag.copy()
                    tag['column'] = {'name': key, 'OID': value}
                    tags.append(tag)
                else:
                    tags.append(tag)
            element = {'MIB': mib, 'table': table, 'symbols': symbols, 'metric_tags': tags}
            if 'forced_type' in metric:
                element['forced_type'] = metric['forced_type']
            output.append(element)

        elif 'symbol' in metric:
            key = metric['symbol']

            node = mib_view_controller.mibBuilder.importSymbols(mib, key)[0]
            value = '.'.join([str(i) for i in node.getName()])
            element = {'MIB': mib, 'symbol': {'name': key, 'OID': value}}
            if 'forced_type' in metric:
                element['forced_type'] = metric['forced_type']
            output.append(element)
    print(yaml.dump({'metrics': output}))
