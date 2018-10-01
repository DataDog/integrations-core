# (C) Datadog, Inc. 2010-2016
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import os
import pytest
from datadog_checks.stubs import aggregator
from datadog_checks.exchange_server import ExchangeCheck
from datadog_checks.exchange_server.exchange_server import DEFAULT_COUNTERS

# for reasons unknown, flake8 says that pdh_mocks_fixture is unused, even though
# it's used below.  noqa to suppress that error.
from datadog_test_libs.win.pdh_mocks import pdh_mocks_fixture, initialize_pdh_tests  # noqa: F401

HERE = os.path.abspath(os.path.dirname(__file__))
MINIMAL_INSTANCE = {
    'host': '.',
}

INSTANCE_WITH_TAGS = {
    'host': '.',
    'tags': ['tag1', 'another:tag']
}


@pytest.fixture
def Aggregator():
    aggregator.reset()
    return aggregator


CHECK_NAME = 'exchange_server'

DATABASE_INSTANCES = [
    'Information Store/_Total',
    'Information Store - Mailbox Database 1266275882/_Total',
    'edgetransport/_Total',
    'edgetransport/Transport Mail Database',
    'edgetransport/IP Filtering Database',
]

EXCHANGE_PROCESSES = [
    'MSExchangeHMHost MSExchangeHM 2212',
    'Microsoft.Exchange.Directory.TopologyService',
    'umservice',
    'MSExchangeFrontendTransport',
    'MSExchangeTransportLogSearch LogSearchSvc 4932',
    'Microsoft.Exchange.Store.Service',
    'ForefrontActiveDirectoryConnector',
    'MSExchangeMailboxAssistants',
    'MSExchangeMailboxReplication MSExchMbxRepl 3832',
    'MSExchangeDelivery',
    'msexchangerepl',
    'Microsoft.Exchange.RpcClientAccess.Service',
    'Microsoft.Exchange.ServiceHost EMS 4360',
    'MSExchangeSubmission',
    'MSExchangeThrottling',
    'MSExchangeHMWorker ExHMWorker 4668',
    'Microsoft.Exchange.UM.CallRouter',
    'noderunner noderunner 3876',
    'noderunner noderunner 3376',
    'noderunner noderunner 3736',
    'noderunner noderunner 3956',
    'MSExchangeTransport',
    'EdgeTransport Transport 5732',
    'w3wp EWS 1656',
    'w3wp',
    'w3wp ECP 7404',
    'w3wp AirSync 7704',
    'w3wp OWA 7648',
    'w3wp',
    'w3wp',
    'w3wp RemotePS 8932',
    'w3wp',
    'Microsoft.Exchange.EdgeSyncSvc',
    'Microsoft.Exchange.Store.Worker',
    'w3wp UNKNOWN 9332',
    'powershell EMS 9000',
    'umservice',
    'UMWorkerProcess UM 4304',
    'Microsoft.Exchange.Search.Service',
    'MSExchangeHMHost MSExchangeHM _Total',
    'MSExchangeTransportLogSearch LogSearchSvc _Total',
    'MSExchangeMailboxReplication MSExchMbxRepl _Total',
    'Microsoft.Exchange.ServiceHost EMS _Total',
    'MSExchangeHMWorker ExHMWorker _Total',
    'noderunner noderunner _Total',
    'EdgeTransport Transport _Total',
    'w3wp EWS _Total',
    'w3wp ECP _Total',
    'w3wp AirSync _Total',
    'w3wp OWA _Total',
    'w3wp RemotePS _Total',
    'w3wp UNKNOWN _Total',
    'powershell EMS _Total',
    'UMWorkerProcess UM _Total',
]


PROXY_INSTANCES = [
    'remoteps',
    'ews',
    'ecp',
    'oab',
    'autodiscover',
    'eas',
    'owa',
    'unknown',
    'win-k2olfvr52p5',
    'rpchttp'

]

WEB_SITE_INSTANCES = [
    '_Total',
    'Default Web Site',
    'Exchange Back End',
]

WORKLOAD_INSTANCES = [
    'msexchangemailboxreplication_mailboxreplicationservicehighpriority',
    'msexchangemailboxreplication_mailboxreplicationservice',
    'msexchangemailboxassistants_sitemailboxassistant_site mailbox assistant',
    'msexchangemailboxassistants_peoplerelevanceassistant',
    'msexchangemailboxassistants_oabgeneratorassistant',
    'msexchangemailboxassistants_publicfolderassistant',
    'msexchangemailboxassistants_directoryprocessorassistant',
    'msexchangemailboxassistants_storemaintenanceassistant_storedsmaintenanceassistant',
    'msexchangemailboxassistants_storemaintenanceassistant',
    'msexchangemailboxassistants_umreportingassistant',
    'msexchangemailboxassistants_calendarsyncassistant',
    'msexchangemailboxassistants_topnassistant_topnwordsassistant',
    'msexchangemailboxassistants_sharingpolicyassistant',
    'msexchangemailboxassistants_calendarrepairassistant',
    'msexchangemailboxassistants_junkemailoptionscommitterassistant',
    'msexchangemailboxassistants_elcassistant',
]

CLIENT_TYPE_INSTANCES = [
    'ediscoverysearch',
    'publicfoldersystem',
    'simplemigration',
    'loadgen',
    'storeactivemonitoring',
    'teammailbox',
    'sms',
    'inference',
    'maintenance',
    'ha',
    'transportsync',
    'migration',
    'momt',
    'timebasedassistants',
    'approvalapi',
    'webservices',
    'unifiedmessaging',
    'monitoring',
    'management',
    'elc',
    'availabilityservice',
    'contentindexing',
    'rpchttp',
    'popimap',
    'owa',
    'eventbasedassistants',
    'airsync',
    'transport',
    'user',
    'administrator',
    'system',
    '_total',
]

METRIC_INSTANCES = {
    'exchange.adaccess_domain_controllers.ldap_read': ['win-k2olfvr52p5.croissant.datad0g.com'],
    'exchange.adaccess_domain_controllers.ldap_search': ['win-k2olfvr52p5.croissant.datad0g.com'],
    'exchange.adaccess_processes.ldap_read': EXCHANGE_PROCESSES,
    'exchange.adaccess_processes.ldap_search': EXCHANGE_PROCESSES,

    'exchange.processor.cpu_time': None,
    'exchange.processor.cpu_user': None,
    'exchange.processor.cpu_privileged': None,
    'exchange.processor.queue_length': None,

    'exchange.memory.available': None,
    'exchange.memory.committed': None,

    'exchange.network.outbound_errors': ['AWS PV Network Device', 'isatap.{C7BAFAFE-DBF4-4C76-B406-8A25283E4CF9}'],
    'exchange.network.tcpv6.connection_failures': None,
    'exchange.network.tcpv4.conns_reset': None,
    'exchange.network.tcpv4.conns_reset': None,

    'exchange.netlogon.semaphore_waiters': ['_Total'],
    'exchange.netlogon.semaphore_holders': ['_Total'],
    'exchange.netlogon.semaphore_acquires': ['_Total'],
    'exchange.netlogon.semaphore_timeouts': ['_Total'],
    'exchange.netlogon.semaphore_hold_time': ['_Total'],

    # Database counters
    'exchange.database.io_reads_avg_latency': DATABASE_INSTANCES,
    'exchange.database.io_writes_avg_latency': DATABASE_INSTANCES,
    'exchange.database.io_log_writes_avg_latency': DATABASE_INSTANCES,
    'exchange.database.io_db_reads_recovery_avg_latency': DATABASE_INSTANCES,
    'exchange.database.io_db_writes_recovery_avg_latency': DATABASE_INSTANCES,
    'exchange.database.io_db_reads_attached_persec': DATABASE_INSTANCES,
    'exchange.database.io_db_writes_attached_persec': DATABASE_INSTANCES,
    'exchange.database.io_log_writes_persec': DATABASE_INSTANCES,
    'exchange.activemanager.database_mounted': None,

    # RPC Client Access Counters
    'exchange.rpc.averaged_latency': None,
    'exchange.rpc.requests': None,
    'exchange.rpc.active_user_count': None,
    'exchange.rpc.conn_count': None,
    'exchange.rpc.ops_persec': None,
    'exchange.rpc.user_count': None,

    # HTTP Proxy Counters
    'exchange.httpproxy.server_locator_latency': PROXY_INSTANCES,
    'exchange.httpproxy.avg_auth_latency': PROXY_INSTANCES,
    'exchange.httpproxy.clientaccess_processing_latency': PROXY_INSTANCES,
    'exchange.httpproxy.mailbox_proxy_failure_rate': PROXY_INSTANCES,
    'exchange.httpproxy.outstanding_requests': PROXY_INSTANCES,
    'exchange.httpproxy.proxy_requests_persec': PROXY_INSTANCES,
    'exchange.httpproxy.requests_persec': PROXY_INSTANCES,

    # Information Store Counters
    'exchange.is.store.rpc_requests': ['mailbox database 1266275882', '_total'],
    'exchange.is.clienttype.rpc_latency': CLIENT_TYPE_INSTANCES,
    'exchange.is.store.rpc_latency': ['mailbox database 1266275882', '_total'],
    'exchange.is.store.rpc_ops_persec': ['mailbox database 1266275882', '_total'],
    'exchange.is.clienttype.rpc_ops_persec': CLIENT_TYPE_INSTANCES,

    # Client Access Server Counters
    'exchange.activesync.requests_persec': None,
    'exchange.activesync.ping_pending': None,
    'exchange.activesync.sync_persec': None,
    'exchange.owa.unique_users': None,
    'exchange.owa.requests_persec': None,
    'exchange.autodiscover.requests_persec': None,
    'exchange.ws.requests_persec': None,

    'exchange.ws.current_connections_total': None,
    'exchange.ws.current_connections_default_website': WEB_SITE_INSTANCES,
    'exchange.ws.connection_attempts': None,
    'exchange.ws.other_attempts': None,

    # Workload Management Counters
    'exchange.workload_management.active_tasks': WORKLOAD_INSTANCES,
    'exchange.workload_management.completed_tasks': WORKLOAD_INSTANCES,
    'exchange.workload_management.queued_tasks': WORKLOAD_INSTANCES,
}


# flake8 then says this is a redefinition of unused, which it's not.
@pytest.mark.usefixtures("pdh_mocks_fixture")  # noqa: F811
def test_basic_check(Aggregator, pdh_mocks_fixture):
    initialize_pdh_tests()
    instance = MINIMAL_INSTANCE
    c = ExchangeCheck(CHECK_NAME, {}, {}, [instance])
    c.check(instance)

    for metric_def in DEFAULT_COUNTERS:
        metric = metric_def[3]
        instances = METRIC_INSTANCES.get(metric)
        if instances is not None:
            for inst in instances:
                Aggregator.assert_metric(metric, tags=["instance:%s" % inst], count=1)
        else:
            Aggregator.assert_metric(metric, tags=None, count=1)

    assert Aggregator.metrics_asserted_pct == 100.0
