# More examples are at https://dsuch.github.io/pymqi/examples.html
# or in code/examples in the source distribution.

import pymqi

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
message = queue.get()
print(message)
queue.close()

qmgr.disconnect()
