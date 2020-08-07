import netsnmp

serv = "localhost"
snmp_pass = "f5"

sess_config = {
    'Version': 2,
    'DestHost': '{}:{}'.format(serv, 1161),
    'Community': snmp_pass,
    'UseNumeric': True,
    # 'RetryNoSuch': True,
    # 'BestGuess': True,
}
session = netsnmp.Session(**sess_config)
session.RetryNoSuch = 1
session.UseEnums = 1
session.UseLongNames = 1

oids = ['1.3.6.1.2.1.31.1.1.1.6']

varlist = netsnmp.VarList(*[netsnmp.Varbind(".{}".format(o)) for o in oids])

# oid = netsnmp.VarList('.1.3.6.1.2.1.1.5.0')
var = netsnmp.VarList(netsnmp.Varbind('.1.3.6.1.2.1.31.1.1'))
snmp_res = session.getnext(varlist)

for x in varlist:
    print("{} : {} => {}".format(x.tag, x.iid, x.val))
