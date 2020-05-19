# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import sys
from io import StringIO
import os

import click
import yaml
from pysnmp.smi import builder
from pysnmp.smi.error import SmiError

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


@snmp.command(context_settings=CONTEXT_SETTINGS, short_help='Generate metadata.csv from profile')
@click.argument('profile_path')
@click.pass_context
def metadata_from_profile(ctx, profile_path):
    """
    Generate metadata.csv from profile.

    You'll need to install pysnmp and pysnmp-mibs manually beforehand.

    Build .py from MIB using:

        mibdump.py --generate-mib-texts --mib-source <MIB_DIR> <MIB_NAME>
        # --generate-mib-texts is needed to will include the descriptions
    """
    # Leave imports in function to not add the dependencies
    from pysnmp import hlapi
    from pysnmp.smi import view
    from pysnmp.smi.error import MibNotFoundError

    snmp_engine = hlapi.SnmpEngine()
    mib_builder = snmp_engine.getMibBuilder()

    from os.path import expanduser
    home = expanduser("~")
    MIBDIR = os.path.join(home, '.pysnmp', 'mibs')
    mibSources = mib_builder.getMibSources() + (builder.DirMibSource(MIBDIR),)
    mib_builder.setMibSources(*mibSources)
    mib_builder.loadTexts = True

    mib_view_controller = view.MibViewController(mib_builder)

    with open(profile_path) as f:
        data = yaml.safe_load(f.read())

    def _bulid_metric_row(symbol_name, forced_type=None):
        try:
            node = mib_view_controller.mibBuilder.importSymbols(mib, symbol_name)[0]
        except (TypeError, SmiError) as e:
            sys.stderr.write("[ERROR] Fail to process symbol: {:30}. Error: {}\n".format(str(symbol_name), e))
            node = None

        metric_type = metric_desc = 'UNKNOWN'

        if node:
            metric_type = get_type(node.syntax)
            metric_desc = node.getDescription()

        if forced_type:
            metric_type = forced_type
        row = {
            'metric_name': "snmp.{}".format(symbol_name),
            'metric_type': metric_type,
            'interval': None,
            'unit_name': None,
            'per_unit_name': None,
            'description': metric_desc,
            'orientation': None,
            'integration': 'snmp',
            'short_name': None,
        }
        return row

    metrics = []
    for metric in data['metrics']:
        mib = metric['MIB']
        # try:
        #     mib_view_controller.mibBuilder.loadModule(mib)
        # except MibNotFoundError:
        #     fetch_mib(mib)
        if 'table' in metric:
            for symbol in metric['symbols']:
                metrics.append(_bulid_metric_row(symbol['name'], metric.get('forced_type')))
        elif 'symbol' in metric:
            metrics.append(_bulid_metric_row(metric['symbol']['name'], metric.get('forced_type')))
        elif 'name' in metric:
            metrics.append(_bulid_metric_row(metric['name'], metric.get('forced_type')))
    import csv

    output = StringIO()
    w = csv.DictWriter(output, metrics[0].keys())
    w.writeheader()
    w.writerows(metrics)
    print(output.getvalue())


SNMP_COUNTER_CLASSES = {
    'Counter32',
    'Counter64',
    # Additional types that are not part of the SNMP protocol (see RFC 2856).
    'ZeroBasedCounter64',
}

SNMP_GAUGE_CLASSES = {
    'Gauge32',
    'Integer',
    'Integer32',
    'Unsigned32',
    # Additional types that are not part of the SNMP protocol (see RFC 2856).
    'CounterBasedGauge64',
}


def get_type(obj):
    name = obj.__class__.__name__
    if name in SNMP_COUNTER_CLASSES:
        return 'count'
    elif name in SNMP_GAUGE_CLASSES:
        return 'gauge'
    return 'UNKNOWN'
