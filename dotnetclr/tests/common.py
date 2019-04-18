# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
MINIMAL_INSTANCE = {'host': '.'}

CHECK_NAME = 'active_directory'

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
