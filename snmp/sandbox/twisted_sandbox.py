from twisted.internet.defer import DeferredList
from twisted.internet.task import react
from pysnmp.hlapi.twisted import *


def success(args, hostname):
    (errorStatus, errorIndex, varBinds) = args

    if errorStatus:
        print('%s: %s at %s' % (hostname,
                                errorStatus.prettyPrint(),
                                errorIndex and varBinds[int(errorIndex) - 1][0] or '?'))
    else:
        for varBind in varBinds:
            print(' = '.join([x.prettyPrint() for x in varBind]))


def failure(errorIndication, hostname):
    print('%s failure: %s' % (hostname, errorIndication))


# noinspection PyUnusedLocal
def getSystem(reactor, hostname):
    snmpEngine = SnmpEngine()

    def getScalar(objectType):
        d = getCmd(snmpEngine,
                   CommunityData('public', mpModel=0),
                   UdpTransportTarget((hostname, 1161)),
                   ContextData(),
                   objectType)
        d.addCallback(success, hostname).addErrback(failure, hostname)
        return d

    return DeferredList(
        [
            getScalar(ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysDescr', 0))),
            getScalar(ObjectType(ObjectIdentity('SNMPv2-MIB', 'sysLocation', 0))),
        ]
    )


react(getSystem, ['localhost'])
