# (C) Datadog, Inc. 2020
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import sys

import yaml
from pysnmp import hlapi
from pysnmp.smi import view


def main(yaml_file):
    """
    Do OID translation in a SNMP profile. This isn't a plain replacement, as it
    doesn't preserve comments and indent, but it should automate most of the
    work.
    """
    snmp_engine = hlapi.SnmpEngine()
    mib_builder = snmp_engine.getMibBuilder()

    mib_view_controller = view.MibViewController(mib_builder)

    output = []
    with open(yaml_file) as f:
        data = yaml.safe_load(f.read())

        for metric in data['metrics']:
            mib = metric['MIB']
            mib_view_controller.mibBuilder.loadModule(mib)
            if 'table' in metric:
                table = metric['table']
                node = mib_view_controller.mibBuilder.importSymbols(mib, table)[0]
                value = ".".join([str(i) for i in node.getName()])
                table = {'name': table, 'OID': value}
                symbols = []
                for symbol in metric['symbols']:
                    node = mib_view_controller.mibBuilder.importSymbols(mib, symbol)[0]
                    value = ".".join([str(i) for i in node.getName()])
                    symbols.append({'name': symbol, 'OID': value})
                tags = []
                for tag in metric['metric_tags']:
                    if 'column' in tag:
                        tag_mib = tag.get('MIB', mib)
                        key = tag['column']
                        node = mib_view_controller.mibBuilder.importSymbols(tag_mib, key)[0]
                        value = ".".join([str(i) for i in node.getName()])
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
                value = ".".join([str(i) for i in node.getName()])
                element = {'MIB': mib, 'symbol': {'name': key, 'OID': value}}
                if 'forced_type' in metric:
                    element['forced_type'] = metric['forced_type']
                output.append(element)
        print(yaml.dump({'metrics': output}))


if __name__ == '__main__':
    main(sys.argv[1])
