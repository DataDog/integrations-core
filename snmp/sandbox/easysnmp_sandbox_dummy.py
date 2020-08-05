import os

os.environ['MIBDIRS'] = '/Users/alexandre.yang/repos/alexyang/workspaces/integrations-core-ws/integrations-core/snmp/tests/mibs'
os.environ['MIBS'] = 'DUMMY-MIB'

from easysnmp import Session

def print_item(item):
    print('{oid}.{oid_index} {snmp_type} = {value}'.format(
        oid=item.oid,
        oid_index=item.oid_index,
        snmp_type=item.snmp_type,
        value=item.value
    ))

session = Session(hostname='localhost', community='dummy', version=2, remote_port=1161)

varbinds = session.get([
    ('dummyCounterGauge'),
])

for item in varbinds:
    print_item(item)
