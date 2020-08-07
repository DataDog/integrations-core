import netsnmp

serv = "127.0.0.1"
snmp_pass = "public"

oid = netsnmp.VarList('.1.3.6.1.2.1.1.6.0')
snmp_res = netsnmp.snmpwalk(oid, Version=2, DestHost=serv, Community=snmp_pass)

print("snmp_res", snmp_res)
for x in oid:
    print("snmp_res:: ", x.iid, " = ", x.val)
