from easysnmp import Session

def print_item(item):
    print('{oid}.{oid_index} {snmp_type} = {value}'.format(
        oid=item.oid,
        oid_index=item.oid_index,
        snmp_type=item.snmp_type,
        value=item.value
    ))



# Create an SNMP session to be used for all our requests
session = Session(hostname='localhost', community='public', version=2, remote_port=1161)

# You may retrieve an individual OID using an SNMP GET
location = session.get('sysLocation.0')

# You may also specify the OID as a tuple (name, index)
# Note: the index is specified as a string as it can be of other types than
# just a regular integer
contact = session.get(('sysContact', '0'))

print_item(contact)

# # And of course, you may use the numeric OID too
# description = session.get('.1.3.6.1.2.1.1.1.0')
#
# # Set a variable using an SNMP SET
# session.set('sysLocation.0', 'The SNMP Lab')
#
# # Perform an SNMP walk
# system_items = session.walk('system')
#
#
# # Each returned item can be used normally as its related type (str or int)
# # but also has several extended attributes with SNMP-specific information
# for item in system_items:
#     print_item(item)
#
