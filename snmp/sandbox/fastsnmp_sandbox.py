from fastsnmp import snmp_poller

hosts = ("127.0.0.1",)
# oids in group must be with same indexes
oid_group = {"1.3.6.1.2.1.2.2.1.2": "ifDescr",
             "1.3.6.1.2.1.2.2.1.10": "ifInOctets",
             }

community = "public"
snmp_data = snmp_poller.poller(hosts, [list(oid_group)], community, msg_type='Get')
for d in snmp_data:
    print("host=%s oid=%s.%s value=%s" % (d[0], oid_group[d[1]], d[2], d[3]))
