# More examples are at https://dsuch.github.io/pymqi/examples.html
# or in code/examples in the source distribution.

import pymqi
import mqtools.MQ as MQ # for formatMQMD
import mqtools.mqpcf as MQPCF
from pprint import pprint

queue_manager = 'datadog'
channel = 'DEV.ADMIN.SVRCONN'
host = 'localhost'
port = '11414'
queue_name = 'DEV.QUEUE.1'
conn_info = '%s(%s)' % (host, port)
user = 'admin'
password = 'passw0rd'

def _get_channel_definition():
    # type: (IBMMQConfig) -> pymqi.CD
    cd = pymqi.CD()
    cd.ChannelName = pymqi.ensure_bytes(channel)
    cd.ConnectionName = pymqi.ensure_bytes(conn_info)
    cd.ChannelType = pymqi.CMQC.MQCHT_CLNTCONN
    cd.TransportType = pymqi.CMQC.MQXPT_TCP
    cd.Version = 8
    return cd

channel_definition = _get_channel_definition()
qmgr = pymqi.QueueManager(None)

# qmgr = pymqi.connect(queue_manager, channel, conn_info, user, password)

kwargs = {'user': user, 'password': password, 'cd': channel_definition}

qmgr.connect_with_options(queue_manager, **kwargs)


# queue = pymqi.Queue(qmgr, queue_name)
queue = pymqi.Queue(qmgr, "SYSTEM.ADMIN.STATISTICS.QUEUE")

md = pymqi.MD()
gmo = pymqi.GMO()

gmo.Options = pymqi.CMQC.MQGMO_WAIT | pymqi.CMQC.MQGMO_FAIL_IF_QUIESCING| pymqi.CMQC.MQGMO_CONVERT
gmo.WaitInterval = 20 * 1000  # 20  seconds

msg = queue.get_rfh2(None, md, gmo)
newMD = MQ.format_MQMD(md)

MQPCF.eprint("MQMD:",newMD )
# MQMD: {'StrucId': 'MD', 'Version': 1, 'Report': 'NONE', 'MsgType': 'DATAGRAM', 'Expiry': -1, 'Feedback': 'NONE', 'Encoding': 546, 'CodedCharSetId': 1208, 'Format': 'MQADMIN', 'Priority': 0, 'Persistence': 'NOT_PERSISTENT', 'MsgId': '0x414d512064617461646f6720202020204500dc5ec2520020', 'CorrelId': '0x000000000000000000000000000000000000000000000000', 'BackoutCount': 0, 'ReplyToQ': '', 'ReplyToQMgr': 'datadog', 'UserIdentifier': '', 'AccountingToken': '0x0000000000000000000000000000000000000000000000000000000000000000', 'ApplIdentityData': '', 'PutApplType': 'QMGR', 'PutApplName': 'datadog', 'PutDate': '20200606', 'PutTime': '22401711', 'ApplOriginData': '', 'GroupId': '0x000000000000000000000000000000000000000000000000', 'MsgSeqNumber': 1, 'Offset': 0, 'MsgFlags': 0, 'OriginalLength': -1}

msg = queue.get()

mqpcf = MQPCF.mqpcf()

PCFheader, PCFdata  = mqpcf.parse_data(buffer=msg, strip="yes", debug=True)
print(">>> PCFheader")
pprint(PCFheader)
print(">>> PCFdata")
pprint(PCFdata)
# print("LEN:", len(message))
# print("MSG:")
# print(message)

# m_desc, get_opts = pymqi.common_q_args()

# m_desc.unpack(message[:364])
# print(m_desc)

queue.close()

qmgr.disconnect()

