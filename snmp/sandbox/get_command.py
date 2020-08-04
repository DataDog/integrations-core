from pysnmp.entity.engine import SnmpEngine
from pysnmp.entity.rfc3413 import cmdgen
from pysnmp.hlapi.asyncore.cmdgen import vbProcessor, ObjectType, ObjectIdentity, UdpTransportTarget, lcd, \
    CommunityData, ContextData


def snmp_get(snmpEngine, target, context_data, oids):
    lookup_mib = False

    def callback(  # type: ignore
        snmpEngine, sendRequestHandle, errorIndication, errorStatus, errorIndex, varBinds, cbCtx
    ):
        var_binds = vbProcessor.unmakeVarBinds(snmpEngine, varBinds, lookup_mib)

        cbCtx['error'] = errorIndication
        cbCtx['var_binds'] = var_binds
        for varBind in varBinds:
            print(' = '.join([x.prettyPrint() for x in varBind]))


    ctx = {}  # type: Dict[str, Any]

    var_binds = vbProcessor.makeVarBinds(snmpEngine, oids)

    cmdgen.GetCommandGenerator().sendVarBinds(
        snmpEngine,
        target,
        None,  # config._context_data.contextEngineId,
        context_data.contextName,  # config._context_data.contextName,
        var_binds,
        callback,
        ctx,
    )

    snmpEngine.transportDispatcher.runDispatcher()

    return ctx['var_binds']



snmpEngine = SnmpEngine()

transport = UdpTransportTarget(('localhost', 1161))
auth_data = CommunityData('public', mpModel=1)
context_data = ContextData(None, '')
target, _ = lcd.configure(snmpEngine, auth_data, transport, context_data)

snmp_get(snmpEngine, target, context_data, [ObjectType(ObjectIdentity('1.3.6.1.4.1.123456789.1.0'))])
