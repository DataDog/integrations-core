import os

os.environ['MIBDIRS'] = '/Users/alexandre.yang/Downloads/my-mibs'
os.environ['MIBS'] = 'F5-BIGIP-SYSTEM-MIB'

from easysnmp import Session

def print_item(item):
    print('{oid}.{oid_index} {snmp_type} = {value}'.format(
        oid=item.oid,
        oid_index=item.oid_index,
        snmp_type=item.snmp_type,
        value=item.value
    ))

session = Session(hostname='localhost', community='f5', version=2, remote_port=1161)

varbinds = session.get([
    ('sysStatMemoryTotal.0'),
    ('sysStatMemoryUsed.0'),
])

for item in varbinds:
    print_item(item)
