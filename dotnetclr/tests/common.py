# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from datadog_checks.dotnetclr.metrics import METRICS_CONFIG

MINIMAL_INSTANCE = {'host': '.'}

INSTANCES = [
    '_Global_',
    'Microsoft.Exchange.Search.Service',
    'UMWorkerProcess',
    'umservice',
    'w3wp',
    'Microsoft.Exchange.Store.Worker',
    'Microsoft.Exchange.EdgeSyncSvc',
    'MSExchangeDelivery',
    'MSExchangeFrontendTransport',
    'Microsoft.Exchange.Store.Service',
    'EdgeTransport',
    'MSExchangeTransport',
    'Microsoft.Exchange.UM.CallRouter',
    'MSExchangeTransportLogSearch',
    'MSExchangeThrottling',
    'MSExchangeHMWorker',
    'MSExchangeSubmission',
    'Microsoft.Exchange.ServiceHost',
    'Microsoft.Exchange.RpcClientAccess.Service',
    'noderunner',
    'msexchangerepl',
    'MSExchangeMailboxReplication',
    'MSExchangeMailboxAssistants',
    'ForefrontActiveDirectoryConnector',
    'Microsoft.Exchange.AntispamUpdateSvc',
    'Ec2Config',
    'Microsoft.Exchange.Directory.TopologyService',
    'WMSvc',
    'MSExchangeHMHost',
    'Microsoft.Exchange.Diagnostics.Service',
    'hostcontrollerservice',
    'Microsoft.ActiveDirectory.WebServices',
]

PERFORMANCE_OBJECTS = {}
for object_name, instances in (('.NET CLR Exceptions', INSTANCES), ('.NET CLR Memory', INSTANCES)):
    PERFORMANCE_OBJECTS[object_name] = (
        instances,
        {counter: [9000] * len(instances) for counter in METRICS_CONFIG[object_name]['counters'][0]},
    )
