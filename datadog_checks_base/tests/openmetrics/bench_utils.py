# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
AMAZON_MSK_JMX_METRICS_MAP = {
    'jmx_config_reload_failure_total': 'jmx.config.reload.failure.total',
    'jmx_config_reload_success_total': 'jmx.config.reload.success.total',
    'jmx_exporter_build_info': 'jmx.exporter.build.info',
    'jmx_scrape_duration_seconds': 'jmx.scrape.duration.seconds',
    'jmx_scrape_error': 'jmx.scrape.error',
    'kafka_cluster_Partition_Value': 'kafka.cluster.Partition.Value',
    'kafka_controller_ControllerChannelManager_50thPercentile': (
        'kafka.controller.ControllerChannelManager.50thPercentile'
    ),
    'kafka_controller_ControllerChannelManager_75thPercentile': (
        'kafka.controller.ControllerChannelManager.75thPercentile'
    ),
    'kafka_controller_ControllerChannelManager_95thPercentile': (
        'kafka.controller.ControllerChannelManager.95thPercentile'
    ),
    'kafka_controller_ControllerChannelManager_98thPercentile': (
        'kafka.controller.ControllerChannelManager.98thPercentile'
    ),
    'kafka_controller_ControllerChannelManager_999thPercentile': (
        'kafka.controller.ControllerChannelManager.999thPercentile'
    ),
    'kafka_controller_ControllerChannelManager_99thPercentile': (
        'kafka.controller.ControllerChannelManager.99thPercentile'
    ),
    'kafka_controller_ControllerChannelManager_Count': 'kafka.controller.ControllerChannelManager.Count',
    'kafka_controller_ControllerChannelManager_FifteenMinuteRate': (
        'kafka.controller.ControllerChannelManager.FifteenMinuteRate'
    ),
    'kafka_controller_ControllerChannelManager_FiveMinuteRate': (
        'kafka.controller.ControllerChannelManager.FiveMinuteRate'
    ),
    'kafka_controller_ControllerChannelManager_Max': 'kafka.controller.ControllerChannelManager.Max',
    'kafka_controller_ControllerChannelManager_Mean': 'kafka.controller.ControllerChannelManager.Mean',
    'kafka_controller_ControllerChannelManager_MeanRate': 'kafka.controller.ControllerChannelManager.MeanRate',
    'kafka_controller_ControllerChannelManager_Min': 'kafka.controller.ControllerChannelManager.Min',
    'kafka_controller_ControllerChannelManager_OneMinuteRate': (
        'kafka.controller.ControllerChannelManager.OneMinuteRate'
    ),
    'kafka_controller_ControllerChannelManager_StdDev': 'kafka.controller.ControllerChannelManager.StdDev',
    'kafka_controller_ControllerChannelManager_Value': 'kafka.controller.ControllerChannelManager.Value',
    'kafka_controller_ControllerEventManager_50thPercentile': 'kafka.controller.ControllerEventManager.50thPercentile',
    'kafka_controller_ControllerEventManager_75thPercentile': 'kafka.controller.ControllerEventManager.75thPercentile',
    'kafka_controller_ControllerEventManager_95thPercentile': 'kafka.controller.ControllerEventManager.95thPercentile',
    'kafka_controller_ControllerEventManager_98thPercentile': 'kafka.controller.ControllerEventManager.98thPercentile',
    'kafka_controller_ControllerEventManager_999thPercentile': (
        'kafka.controller.ControllerEventManager.999thPercentile'
    ),
    'kafka_controller_ControllerEventManager_99thPercentile': 'kafka.controller.ControllerEventManager.99thPercentile',
    'kafka_controller_ControllerEventManager_Count': 'kafka.controller.ControllerEventManager.Count',
    'kafka_controller_ControllerEventManager_Max': 'kafka.controller.ControllerEventManager.Max',
    'kafka_controller_ControllerEventManager_Mean': 'kafka.controller.ControllerEventManager.Mean',
    'kafka_controller_ControllerEventManager_Min': 'kafka.controller.ControllerEventManager.Min',
    'kafka_controller_ControllerEventManager_StdDev': 'kafka.controller.ControllerEventManager.StdDev',
    'kafka_controller_ControllerEventManager_Value': 'kafka.controller.ControllerEventManager.Value',
    'kafka_controller_ControllerStats_50thPercentile': 'kafka.controller.ControllerStats.50thPercentile',
    'kafka_controller_ControllerStats_75thPercentile': 'kafka.controller.ControllerStats.75thPercentile',
    'kafka_controller_ControllerStats_95thPercentile': 'kafka.controller.ControllerStats.95thPercentile',
    'kafka_controller_ControllerStats_98thPercentile': 'kafka.controller.ControllerStats.98thPercentile',
    'kafka_controller_ControllerStats_999thPercentile': 'kafka.controller.ControllerStats.999thPercentile',
    'kafka_controller_ControllerStats_99thPercentile': 'kafka.controller.ControllerStats.99thPercentile',
    'kafka_controller_ControllerStats_Count': 'kafka.controller.ControllerStats.Count',
    'kafka_controller_ControllerStats_FifteenMinuteRate': 'kafka.controller.ControllerStats.FifteenMinuteRate',
    'kafka_controller_ControllerStats_FiveMinuteRate': 'kafka.controller.ControllerStats.FiveMinuteRate',
    'kafka_controller_ControllerStats_Max': 'kafka.controller.ControllerStats.Max',
    'kafka_controller_ControllerStats_Mean': 'kafka.controller.ControllerStats.Mean',
    'kafka_controller_ControllerStats_MeanRate': 'kafka.controller.ControllerStats.MeanRate',
    'kafka_controller_ControllerStats_Min': 'kafka.controller.ControllerStats.Min',
    'kafka_controller_ControllerStats_OneMinuteRate': 'kafka.controller.ControllerStats.OneMinuteRate',
    'kafka_controller_ControllerStats_StdDev': 'kafka.controller.ControllerStats.StdDev',
    'kafka_controller_KafkaController_Value': 'kafka.controller.KafkaController.Value',
    'kafka_coordinator_group_GroupMetadataManager_Value': 'kafka.coordinator.group.GroupMetadataManager.Value',
    'kafka_coordinator_transaction_TransactionMarkerChannelManager_Value': (
        'kafka.coordinator.transaction.TransactionMarkerChannelManager.Value'
    ),
    'kafka_log_Log_Value': 'kafka.log.Log.Value',
    'kafka_log_LogCleaner_Value': 'kafka.log.LogCleaner.Value',
    'kafka_log_LogCleanerManager_Value': 'kafka.log.LogCleanerManager.Value',
    'kafka_log_LogManager_Value': 'kafka.log.LogManager.Value',
    'kafka_network_Acceptor_Count': 'kafka.network.Acceptor.Count',
    'kafka_network_Acceptor_FifteenMinuteRate': 'kafka.network.Acceptor.FifteenMinuteRate',
    'kafka_network_Acceptor_FiveMinuteRate': 'kafka.network.Acceptor.FiveMinuteRate',
    'kafka_network_Acceptor_MeanRate': 'kafka.network.Acceptor.MeanRate',
    'kafka_network_Acceptor_OneMinuteRate': 'kafka.network.Acceptor.OneMinuteRate',
    'kafka_network_Processor_Value': 'kafka.network.Processor.Value',
    'kafka_network_RequestChannel_Value': 'kafka.network.RequestChannel.Value',
    'kafka_network_RequestMetrics_50thPercentile': 'kafka.network.RequestMetrics.50thPercentile',
    'kafka_network_RequestMetrics_75thPercentile': 'kafka.network.RequestMetrics.75thPercentile',
    'kafka_network_RequestMetrics_95thPercentile': 'kafka.network.RequestMetrics.95thPercentile',
    'kafka_network_RequestMetrics_98thPercentile': 'kafka.network.RequestMetrics.98thPercentile',
    'kafka_network_RequestMetrics_999thPercentile': 'kafka.network.RequestMetrics.999thPercentile',
    'kafka_network_RequestMetrics_99thPercentile': 'kafka.network.RequestMetrics.99thPercentile',
    'kafka_network_RequestMetrics_Count': 'kafka.network.RequestMetrics.Count',
    'kafka_network_RequestMetrics_FifteenMinuteRate': 'kafka.network.RequestMetrics.FifteenMinuteRate',
    'kafka_network_RequestMetrics_FiveMinuteRate': 'kafka.network.RequestMetrics.FiveMinuteRate',
    'kafka_network_RequestMetrics_Max': 'kafka.network.RequestMetrics.Max',
    'kafka_network_RequestMetrics_Mean': 'kafka.network.RequestMetrics.Mean',
    'kafka_network_RequestMetrics_MeanRate': 'kafka.network.RequestMetrics.MeanRate',
    'kafka_network_RequestMetrics_Min': 'kafka.network.RequestMetrics.Min',
    'kafka_network_RequestMetrics_OneMinuteRate': 'kafka.network.RequestMetrics.OneMinuteRate',
    'kafka_network_RequestMetrics_StdDev': 'kafka.network.RequestMetrics.StdDev',
    'kafka_network_SocketServer_Value': 'kafka.network.SocketServer.Value',
    'kafka_security_SimpleAclAuthorizer_Count': 'kafka.security.SimpleAclAuthorizer.Count',
    'kafka_security_SimpleAclAuthorizer_FifteenMinuteRate': 'kafka.security.SimpleAclAuthorizer.FifteenMinuteRate',
    'kafka_security_SimpleAclAuthorizer_FiveMinuteRate': 'kafka.security.SimpleAclAuthorizer.FiveMinuteRate',
    'kafka_security_SimpleAclAuthorizer_MeanRate': 'kafka.security.SimpleAclAuthorizer.MeanRate',
    'kafka_security_SimpleAclAuthorizer_OneMinuteRate': 'kafka.security.SimpleAclAuthorizer.OneMinuteRate',
    'kafka_server_BrokerTopicMetrics_Count': 'kafka.server.BrokerTopicMetrics.Count',
    'kafka_server_BrokerTopicMetrics_FifteenMinuteRate': 'kafka.server.BrokerTopicMetrics.FifteenMinuteRate',
    'kafka_server_BrokerTopicMetrics_FiveMinuteRate': 'kafka.server.BrokerTopicMetrics.FiveMinuteRate',
    'kafka_server_BrokerTopicMetrics_MeanRate': 'kafka.server.BrokerTopicMetrics.MeanRate',
    'kafka_server_BrokerTopicMetrics_OneMinuteRate': 'kafka.server.BrokerTopicMetrics.OneMinuteRate',
    'kafka_server_DelayedFetchMetrics_Count': 'kafka.server.DelayedFetchMetrics.Count',
    'kafka_server_DelayedFetchMetrics_FifteenMinuteRate': 'kafka.server.DelayedFetchMetrics.FifteenMinuteRate',
    'kafka_server_DelayedFetchMetrics_FiveMinuteRate': 'kafka.server.DelayedFetchMetrics.FiveMinuteRate',
    'kafka_server_DelayedFetchMetrics_MeanRate': 'kafka.server.DelayedFetchMetrics.MeanRate',
    'kafka_server_DelayedFetchMetrics_OneMinuteRate': 'kafka.server.DelayedFetchMetrics.OneMinuteRate',
    'kafka_server_DelayedOperationPurgatory_Value': 'kafka.server.DelayedOperationPurgatory.Value',
    'kafka_server_Fetch_queue_size': 'kafka.server.Fetch.queue.size',
    'kafka_server_FetchSessionCache_Count': 'kafka.server.FetchSessionCache.Count',
    'kafka_server_FetchSessionCache_FifteenMinuteRate': 'kafka.server.FetchSessionCache.FifteenMinuteRate',
    'kafka_server_FetchSessionCache_FiveMinuteRate': 'kafka.server.FetchSessionCache.FiveMinuteRate',
    'kafka_server_FetchSessionCache_MeanRate': 'kafka.server.FetchSessionCache.MeanRate',
    'kafka_server_FetchSessionCache_OneMinuteRate': 'kafka.server.FetchSessionCache.OneMinuteRate',
    'kafka_server_FetchSessionCache_Value': 'kafka.server.FetchSessionCache.Value',
    'kafka_server_FetcherLagMetrics_Value': 'kafka.server.FetcherLagMetrics.Value',
    'kafka_server_FetcherStats_Count': 'kafka.server.FetcherStats.Count',
    'kafka_server_FetcherStats_FifteenMinuteRate': 'kafka.server.FetcherStats.FifteenMinuteRate',
    'kafka_server_FetcherStats_FiveMinuteRate': 'kafka.server.FetcherStats.FiveMinuteRate',
    'kafka_server_FetcherStats_MeanRate': 'kafka.server.FetcherStats.MeanRate',
    'kafka_server_FetcherStats_OneMinuteRate': 'kafka.server.FetcherStats.OneMinuteRate',
    'kafka_server_KafkaRequestHandlerPool_Count': 'kafka.server.KafkaRequestHandlerPool.Count',
    'kafka_server_KafkaRequestHandlerPool_FifteenMinuteRate': 'kafka.server.KafkaRequestHandlerPool.FifteenMinuteRate',
    'kafka_server_KafkaRequestHandlerPool_FiveMinuteRate': 'kafka.server.KafkaRequestHandlerPool.FiveMinuteRate',
    'kafka_server_KafkaRequestHandlerPool_MeanRate': 'kafka.server.KafkaRequestHandlerPool.MeanRate',
    'kafka_server_KafkaRequestHandlerPool_OneMinuteRate': 'kafka.server.KafkaRequestHandlerPool.OneMinuteRate',
    'kafka_server_KafkaServer_Value': 'kafka.server.KafkaServer.Value',
    'kafka_server_LeaderReplication_byte_rate': 'kafka.server.LeaderReplication.byte.rate',
    'kafka_server_Produce_queue_size': 'kafka.server.Produce.queue.size',
    'kafka_server_ReplicaAlterLogDirsManager_Value': 'kafka.server.ReplicaAlterLogDirsManager.Value',
    'kafka_server_ReplicaFetcherManager_Value': 'kafka.server.ReplicaFetcherManager.Value',
    'kafka_server_ReplicaManager_Count': 'kafka.server.ReplicaManager.Count',
    'kafka_server_ReplicaManager_FifteenMinuteRate': 'kafka.server.ReplicaManager.FifteenMinuteRate',
    'kafka_server_ReplicaManager_FiveMinuteRate': 'kafka.server.ReplicaManager.FiveMinuteRate',
    'kafka_server_ReplicaManager_MeanRate': 'kafka.server.ReplicaManager.MeanRate',
    'kafka_server_ReplicaManager_OneMinuteRate': 'kafka.server.ReplicaManager.OneMinuteRate',
    'kafka_server_ReplicaManager_Value': 'kafka.server.ReplicaManager.Value',
    'kafka_server_Request_queue_size': 'kafka.server.Request.queue.size',
    'kafka_server_SessionExpireListener_Count': 'kafka.server.SessionExpireListener.Count',
    'kafka_server_SessionExpireListener_FifteenMinuteRate': 'kafka.server.SessionExpireListener.FifteenMinuteRate',
    'kafka_server_SessionExpireListener_FiveMinuteRate': 'kafka.server.SessionExpireListener.FiveMinuteRate',
    'kafka_server_SessionExpireListener_MeanRate': 'kafka.server.SessionExpireListener.MeanRate',
    'kafka_server_SessionExpireListener_OneMinuteRate': 'kafka.server.SessionExpireListener.OneMinuteRate',
    'kafka_server_ZooKeeperClientMetrics_50thPercentile': 'kafka.server.ZooKeeperClientMetrics.50thPercentile',
    'kafka_server_ZooKeeperClientMetrics_75thPercentile': 'kafka.server.ZooKeeperClientMetrics.75thPercentile',
    'kafka_server_ZooKeeperClientMetrics_95thPercentile': 'kafka.server.ZooKeeperClientMetrics.95thPercentile',
    'kafka_server_ZooKeeperClientMetrics_98thPercentile': 'kafka.server.ZooKeeperClientMetrics.98thPercentile',
    'kafka_server_ZooKeeperClientMetrics_999thPercentile': 'kafka.server.ZooKeeperClientMetrics.999thPercentile',
    'kafka_server_ZooKeeperClientMetrics_99thPercentile': 'kafka.server.ZooKeeperClientMetrics.99thPercentile',
    'kafka_server_ZooKeeperClientMetrics_Count': 'kafka.server.ZooKeeperClientMetrics.Count',
    'kafka_server_ZooKeeperClientMetrics_Max': 'kafka.server.ZooKeeperClientMetrics.Max',
    'kafka_server_ZooKeeperClientMetrics_Mean': 'kafka.server.ZooKeeperClientMetrics.Mean',
    'kafka_server_ZooKeeperClientMetrics_Min': 'kafka.server.ZooKeeperClientMetrics.Min',
    'kafka_server_ZooKeeperClientMetrics_StdDev': 'kafka.server.ZooKeeperClientMetrics.StdDev',
    'kafka_server_controller_channel_metrics_connection_close_rate': (
        'kafka.server.controller.channel.metrics.connection.close.rate'
    ),
    'kafka_server_controller_channel_metrics_connection_close_total': (
        'kafka.server.controller.channel.metrics.connection.close.total'
    ),
    'kafka_server_controller_channel_metrics_connection_count': (
        'kafka.server.controller.channel.metrics.connection.count'
    ),
    'kafka_server_controller_channel_metrics_connection_creation_rate': (
        'kafka.server.controller.channel.metrics.connection.creation.rate'
    ),
    'kafka_server_controller_channel_metrics_connection_creation_total': (
        'kafka.server.controller.channel.metrics.connection.creation.total'
    ),
    'kafka_server_controller_channel_metrics_failed_authentication_rate': (
        'kafka.server.controller.channel.metrics.failed.authentication.rate'
    ),
    'kafka_server_controller_channel_metrics_failed_authentication_total': (
        'kafka.server.controller.channel.metrics.failed.authentication.total'
    ),
    'kafka_server_controller_channel_metrics_failed_reauthentication_rate': (
        'kafka.server.controller.channel.metrics.failed.reauthentication.rate'
    ),
    'kafka_server_controller_channel_metrics_failed_reauthentication_total': (
        'kafka.server.controller.channel.metrics.failed.reauthentication.total'
    ),
    'kafka_server_controller_channel_metrics_incoming_byte_rate': (
        'kafka.server.controller.channel.metrics.incoming.byte.rate'
    ),
    'kafka_server_controller_channel_metrics_incoming_byte_total': (
        'kafka.server.controller.channel.metrics.incoming.byte.total'
    ),
    'kafka_server_controller_channel_metrics_io_ratio': 'kafka.server.controller.channel.metrics.io.ratio',
    'kafka_server_controller_channel_metrics_io_time_ns_avg': 'kafka.server.controller.channel.metrics.io.time.ns.avg',
    'kafka_server_controller_channel_metrics_io_wait_ratio': 'kafka.server.controller.channel.metrics.io.wait.ratio',
    'kafka_server_controller_channel_metrics_io_wait_time_ns_avg': (
        'kafka.server.controller.channel.metrics.io.wait.time.ns.avg'
    ),
    'kafka_server_controller_channel_metrics_io_waittime_total': (
        'kafka.server.controller.channel.metrics.io.waittime.total'
    ),
    'kafka_server_controller_channel_metrics_iotime_total': 'kafka.server.controller.channel.metrics.iotime.total',
    'kafka_server_controller_channel_metrics_network_io_rate': (
        'kafka.server.controller.channel.metrics.network.io.rate'
    ),
    'kafka_server_controller_channel_metrics_network_io_total': (
        'kafka.server.controller.channel.metrics.network.io.total'
    ),
    'kafka_server_controller_channel_metrics_outgoing_byte_rate': (
        'kafka.server.controller.channel.metrics.outgoing.byte.rate'
    ),
    'kafka_server_controller_channel_metrics_outgoing_byte_total': (
        'kafka.server.controller.channel.metrics.outgoing.byte.total'
    ),
    'kafka_server_controller_channel_metrics_reauthentication_latency_avg': (
        'kafka.server.controller.channel.metrics.reauthentication.latency.avg'
    ),
    'kafka_server_controller_channel_metrics_reauthentication_latency_max': (
        'kafka.server.controller.channel.metrics.reauthentication.latency.max'
    ),
    'kafka_server_controller_channel_metrics_request_rate': 'kafka.server.controller.channel.metrics.request.rate',
    'kafka_server_controller_channel_metrics_request_size_avg': (
        'kafka.server.controller.channel.metrics.request.size.avg'
    ),
    'kafka_server_controller_channel_metrics_request_size_max': (
        'kafka.server.controller.channel.metrics.request.size.max'
    ),
    'kafka_server_controller_channel_metrics_request_total': 'kafka.server.controller.channel.metrics.request.total',
    'kafka_server_controller_channel_metrics_response_rate': 'kafka.server.controller.channel.metrics.response.rate',
    'kafka_server_controller_channel_metrics_response_total': 'kafka.server.controller.channel.metrics.response.total',
    'kafka_server_controller_channel_metrics_select_rate': 'kafka.server.controller.channel.metrics.select.rate',
    'kafka_server_controller_channel_metrics_select_total': 'kafka.server.controller.channel.metrics.select.total',
    'kafka_server_controller_channel_metrics_successful_authentication_no_reauth_total': (
        'kafka.server.controller.channel.metrics.successful.authentication.no.reauth.total'
    ),
    'kafka_server_controller_channel_metrics_successful_authentication_rate': (
        'kafka.server.controller.channel.metrics.successful.authentication.rate'
    ),
    'kafka_server_controller_channel_metrics_successful_authentication_total': (
        'kafka.server.controller.channel.metrics.successful.authentication.total'
    ),
    'kafka_server_controller_channel_metrics_successful_reauthentication_rate': (
        'kafka.server.controller.channel.metrics.successful.reauthentication.rate'
    ),
    'kafka_server_controller_channel_metrics_successful_reauthentication_total': (
        'kafka.server.controller.channel.metrics.successful.reauthentication.total'
    ),
    'kafka_server_kafka_metrics_count_count': 'kafka.server.kafka.metrics.count.count',
    'kafka_server_replica_fetcher_metrics_connection_close_rate': (
        'kafka.server.replica.fetcher.metrics.connection.close.rate'
    ),
    'kafka_server_replica_fetcher_metrics_connection_close_total': (
        'kafka.server.replica.fetcher.metrics.connection.close.total'
    ),
    'kafka_server_replica_fetcher_metrics_connection_count': 'kafka.server.replica.fetcher.metrics.connection.count',
    'kafka_server_replica_fetcher_metrics_connection_creation_rate': (
        'kafka.server.replica.fetcher.metrics.connection.creation.rate'
    ),
    'kafka_server_replica_fetcher_metrics_connection_creation_total': (
        'kafka.server.replica.fetcher.metrics.connection.creation.total'
    ),
    'kafka_server_replica_fetcher_metrics_failed_authentication_rate': (
        'kafka.server.replica.fetcher.metrics.failed.authentication.rate'
    ),
    'kafka_server_replica_fetcher_metrics_failed_authentication_total': (
        'kafka.server.replica.fetcher.metrics.failed.authentication.total'
    ),
    'kafka_server_replica_fetcher_metrics_incoming_byte_rate': (
        'kafka.server.replica.fetcher.metrics.incoming.byte.rate'
    ),
    'kafka_server_replica_fetcher_metrics_incoming_byte_total': (
        'kafka.server.replica.fetcher.metrics.incoming.byte.total'
    ),
    'kafka_server_replica_fetcher_metrics_io_ratio': 'kafka.server.replica.fetcher.metrics.io.ratio',
    'kafka_server_replica_fetcher_metrics_io_time_ns_avg': 'kafka.server.replica.fetcher.metrics.io.time.ns.avg',
    'kafka_server_replica_fetcher_metrics_io_wait_ratio': 'kafka.server.replica.fetcher.metrics.io.wait.ratio',
    'kafka_server_replica_fetcher_metrics_io_wait_time_ns_avg': (
        'kafka.server.replica.fetcher.metrics.io.wait.time.ns.avg'
    ),
    'kafka_server_replica_fetcher_metrics_io_waittime_total': 'kafka.server.replica.fetcher.metrics.io.waittime.total',
    'kafka_server_replica_fetcher_metrics_iotime_total': 'kafka.server.replica.fetcher.metrics.iotime.total',
    'kafka_server_replica_fetcher_metrics_network_io_rate': 'kafka.server.replica.fetcher.metrics.network.io.rate',
    'kafka_server_replica_fetcher_metrics_network_io_total': 'kafka.server.replica.fetcher.metrics.network.io.total',
    'kafka_server_replica_fetcher_metrics_outgoing_byte_rate': (
        'kafka.server.replica.fetcher.metrics.outgoing.byte.rate'
    ),
    'kafka_server_replica_fetcher_metrics_outgoing_byte_total': (
        'kafka.server.replica.fetcher.metrics.outgoing.byte.total'
    ),
    'kafka_server_replica_fetcher_metrics_request_rate': 'kafka.server.replica.fetcher.metrics.request.rate',
    'kafka_server_replica_fetcher_metrics_request_size_avg': 'kafka.server.replica.fetcher.metrics.request.size.avg',
    'kafka_server_replica_fetcher_metrics_request_size_max': 'kafka.server.replica.fetcher.metrics.request.size.max',
    'kafka_server_replica_fetcher_metrics_request_total': 'kafka.server.replica.fetcher.metrics.request.total',
    'kafka_server_replica_fetcher_metrics_response_rate': 'kafka.server.replica.fetcher.metrics.response.rate',
    'kafka_server_replica_fetcher_metrics_response_total': 'kafka.server.replica.fetcher.metrics.response.total',
    'kafka_server_replica_fetcher_metrics_select_rate': 'kafka.server.replica.fetcher.metrics.select.rate',
    'kafka_server_replica_fetcher_metrics_select_total': 'kafka.server.replica.fetcher.metrics.select.total',
    'kafka_server_replica_fetcher_metrics_successful_authentication_rate': (
        'kafka.server.replica.fetcher.metrics.successful.authentication.rate'
    ),
    'kafka_server_replica_fetcher_metrics_successful_authentication_total': (
        'kafka.server.replica.fetcher.metrics.successful.authentication.total'
    ),
    'kafka_server_socket_server_metrics_MemoryPoolAvgDepletedPercent': (
        'kafka.server.socket.server.metrics.MemoryPoolAvgDepletedPercent'
    ),
    'kafka_server_socket_server_metrics_MemoryPoolDepletedTimeTotal': (
        'kafka.server.socket.server.metrics.MemoryPoolDepletedTimeTotal'
    ),
    'kafka_server_socket_server_metrics_connection_close_rate': (
        'kafka.server.socket.server.metrics.connection.close.rate'
    ),
    'kafka_server_socket_server_metrics_connection_close_total': (
        'kafka.server.socket.server.metrics.connection.close.total'
    ),
    'kafka_server_socket_server_metrics_connection_count': 'kafka.server.socket.server.metrics.connection.count',
    'kafka_server_socket_server_metrics_connection_creation_rate': (
        'kafka.server.socket.server.metrics.connection.creation.rate'
    ),
    'kafka_server_socket_server_metrics_connection_creation_total': (
        'kafka.server.socket.server.metrics.connection.creation.total'
    ),
    'kafka_server_socket_server_metrics_expired_connections_killed_count': (
        'kafka.server.socket.server.metrics.expired.connections.killed.count'
    ),
    'kafka_server_socket_server_metrics_failed_authentication_rate': (
        'kafka.server.socket.server.metrics.failed.authentication.rate'
    ),
    'kafka_server_socket_server_metrics_failed_authentication_total': (
        'kafka.server.socket.server.metrics.failed.authentication.total'
    ),
    'kafka_server_socket_server_metrics_failed_reauthentication_rate': (
        'kafka.server.socket.server.metrics.failed.reauthentication.rate'
    ),
    'kafka_server_socket_server_metrics_failed_reauthentication_total': (
        'kafka.server.socket.server.metrics.failed.reauthentication.total'
    ),
    'kafka_server_socket_server_metrics_incoming_byte_rate': 'kafka.server.socket.server.metrics.incoming.byte.rate',
    'kafka_server_socket_server_metrics_incoming_byte_total': 'kafka.server.socket.server.metrics.incoming.byte.total',
    'kafka_server_socket_server_metrics_io_ratio': 'kafka.server.socket.server.metrics.io.ratio',
    'kafka_server_socket_server_metrics_io_time_ns_avg': 'kafka.server.socket.server.metrics.io.time.ns.avg',
    'kafka_server_socket_server_metrics_io_wait_ratio': 'kafka.server.socket.server.metrics.io.wait.ratio',
    'kafka_server_socket_server_metrics_io_wait_time_ns_avg': 'kafka.server.socket.server.metrics.io.wait.time.ns.avg',
    'kafka_server_socket_server_metrics_io_waittime_total': 'kafka.server.socket.server.metrics.io.waittime.total',
    'kafka_server_socket_server_metrics_iotime_total': 'kafka.server.socket.server.metrics.iotime.total',
    'kafka_server_socket_server_metrics_network_io_rate': 'kafka.server.socket.server.metrics.network.io.rate',
    'kafka_server_socket_server_metrics_network_io_total': 'kafka.server.socket.server.metrics.network.io.total',
    'kafka_server_socket_server_metrics_outgoing_byte_rate': 'kafka.server.socket.server.metrics.outgoing.byte.rate',
    'kafka_server_socket_server_metrics_outgoing_byte_total': 'kafka.server.socket.server.metrics.outgoing.byte.total',
    'kafka_server_socket_server_metrics_reauthentication_latency_avg': (
        'kafka.server.socket.server.metrics.reauthentication.latency.avg'
    ),
    'kafka_server_socket_server_metrics_reauthentication_latency_max': (
        'kafka.server.socket.server.metrics.reauthentication.latency.max'
    ),
    'kafka_server_socket_server_metrics_request_rate': 'kafka.server.socket.server.metrics.request.rate',
    'kafka_server_socket_server_metrics_request_size_avg': 'kafka.server.socket.server.metrics.request.size.avg',
    'kafka_server_socket_server_metrics_request_size_max': 'kafka.server.socket.server.metrics.request.size.max',
    'kafka_server_socket_server_metrics_request_total': 'kafka.server.socket.server.metrics.request.total',
    'kafka_server_socket_server_metrics_response_rate': 'kafka.server.socket.server.metrics.response.rate',
    'kafka_server_socket_server_metrics_response_total': 'kafka.server.socket.server.metrics.response.total',
    'kafka_server_socket_server_metrics_select_rate': 'kafka.server.socket.server.metrics.select.rate',
    'kafka_server_socket_server_metrics_select_total': 'kafka.server.socket.server.metrics.select.total',
    'kafka_server_socket_server_metrics_successful_authentication_no_reauth_total': (
        'kafka.server.socket.server.metrics.successful.authentication.no.reauth.total'
    ),
    'kafka_server_socket_server_metrics_successful_authentication_rate': (
        'kafka.server.socket.server.metrics.successful.authentication.rate'
    ),
    'kafka_server_socket_server_metrics_successful_authentication_total': (
        'kafka.server.socket.server.metrics.successful.authentication.total'
    ),
    'kafka_server_socket_server_metrics_successful_reauthentication_rate': (
        'kafka.server.socket.server.metrics.successful.reauthentication.rate'
    ),
    'kafka_server_socket_server_metrics_successful_reauthentication_total': (
        'kafka.server.socket.server.metrics.successful.reauthentication.total'
    ),
    'kafka_server_txn_marker_channel_metrics_connection_close_rate': (
        'kafka.server.txn.marker.channel.metrics.connection.close.rate'
    ),
    'kafka_server_txn_marker_channel_metrics_connection_close_total': (
        'kafka.server.txn.marker.channel.metrics.connection.close.total'
    ),
    'kafka_server_txn_marker_channel_metrics_connection_count': (
        'kafka.server.txn.marker.channel.metrics.connection.count'
    ),
    'kafka_server_txn_marker_channel_metrics_connection_creation_rate': (
        'kafka.server.txn.marker.channel.metrics.connection.creation.rate'
    ),
    'kafka_server_txn_marker_channel_metrics_connection_creation_total': (
        'kafka.server.txn.marker.channel.metrics.connection.creation.total'
    ),
    'kafka_server_txn_marker_channel_metrics_failed_authentication_rate': (
        'kafka.server.txn.marker.channel.metrics.failed.authentication.rate'
    ),
    'kafka_server_txn_marker_channel_metrics_failed_authentication_total': (
        'kafka.server.txn.marker.channel.metrics.failed.authentication.total'
    ),
    'kafka_server_txn_marker_channel_metrics_failed_reauthentication_rate': (
        'kafka.server.txn.marker.channel.metrics.failed.reauthentication.rate'
    ),
    'kafka_server_txn_marker_channel_metrics_failed_reauthentication_total': (
        'kafka.server.txn.marker.channel.metrics.failed.reauthentication.total'
    ),
    'kafka_server_txn_marker_channel_metrics_incoming_byte_rate': (
        'kafka.server.txn.marker.channel.metrics.incoming.byte.rate'
    ),
    'kafka_server_txn_marker_channel_metrics_incoming_byte_total': (
        'kafka.server.txn.marker.channel.metrics.incoming.byte.total'
    ),
    'kafka_server_txn_marker_channel_metrics_io_ratio': 'kafka.server.txn.marker.channel.metrics.io.ratio',
    'kafka_server_txn_marker_channel_metrics_io_time_ns_avg': 'kafka.server.txn.marker.channel.metrics.io.time.ns.avg',
    'kafka_server_txn_marker_channel_metrics_io_wait_ratio': 'kafka.server.txn.marker.channel.metrics.io.wait.ratio',
    'kafka_server_txn_marker_channel_metrics_io_wait_time_ns_avg': (
        'kafka.server.txn.marker.channel.metrics.io.wait.time.ns.avg'
    ),
    'kafka_server_txn_marker_channel_metrics_io_waittime_total': (
        'kafka.server.txn.marker.channel.metrics.io.waittime.total'
    ),
    'kafka_server_txn_marker_channel_metrics_iotime_total': 'kafka.server.txn.marker.channel.metrics.iotime.total',
    'kafka_server_txn_marker_channel_metrics_network_io_rate': (
        'kafka.server.txn.marker.channel.metrics.network.io.rate'
    ),
    'kafka_server_txn_marker_channel_metrics_network_io_total': (
        'kafka.server.txn.marker.channel.metrics.network.io.total'
    ),
    'kafka_server_txn_marker_channel_metrics_outgoing_byte_rate': (
        'kafka.server.txn.marker.channel.metrics.outgoing.byte.rate'
    ),
    'kafka_server_txn_marker_channel_metrics_outgoing_byte_total': (
        'kafka.server.txn.marker.channel.metrics.outgoing.byte.total'
    ),
    'kafka_server_txn_marker_channel_metrics_reauthentication_latency_avg': (
        'kafka.server.txn.marker.channel.metrics.reauthentication.latency.avg'
    ),
    'kafka_server_txn_marker_channel_metrics_reauthentication_latency_max': (
        'kafka.server.txn.marker.channel.metrics.reauthentication.latency.max'
    ),
    'kafka_server_txn_marker_channel_metrics_request_rate': 'kafka.server.txn.marker.channel.metrics.request.rate',
    'kafka_server_txn_marker_channel_metrics_request_size_avg': (
        'kafka.server.txn.marker.channel.metrics.request.size.avg'
    ),
    'kafka_server_txn_marker_channel_metrics_request_size_max': (
        'kafka.server.txn.marker.channel.metrics.request.size.max'
    ),
    'kafka_server_txn_marker_channel_metrics_request_total': 'kafka.server.txn.marker.channel.metrics.request.total',
    'kafka_server_txn_marker_channel_metrics_response_rate': 'kafka.server.txn.marker.channel.metrics.response.rate',
    'kafka_server_txn_marker_channel_metrics_response_total': 'kafka.server.txn.marker.channel.metrics.response.total',
    'kafka_server_txn_marker_channel_metrics_select_rate': 'kafka.server.txn.marker.channel.metrics.select.rate',
    'kafka_server_txn_marker_channel_metrics_select_total': 'kafka.server.txn.marker.channel.metrics.select.total',
    'kafka_server_txn_marker_channel_metrics_successful_authentication_no_reauth_total': (
        'kafka.server.txn.marker.channel.metrics.successful.authentication.no.reauth.total'
    ),
    'kafka_server_txn_marker_channel_metrics_successful_authentication_rate': (
        'kafka.server.txn.marker.channel.metrics.successful.authentication.rate'
    ),
    'kafka_server_txn_marker_channel_metrics_successful_authentication_total': (
        'kafka.server.txn.marker.channel.metrics.successful.authentication.total'
    ),
    'kafka_server_txn_marker_channel_metrics_successful_reauthentication_rate': (
        'kafka.server.txn.marker.channel.metrics.successful.reauthentication.rate'
    ),
    'kafka_server_txn_marker_channel_metrics_successful_reauthentication_total': (
        'kafka.server.txn.marker.channel.metrics.successful.reauthentication.total'
    ),
    'kafka_utils_Throttler_Count': 'kafka.utils.Throttler.Count',
    'kafka_utils_Throttler_FifteenMinuteRate': 'kafka.utils.Throttler.FifteenMinuteRate',
    'kafka_utils_Throttler_FiveMinuteRate': 'kafka.utils.Throttler.FiveMinuteRate',
    'kafka_utils_Throttler_MeanRate': 'kafka.utils.Throttler.MeanRate',
    'kafka_utils_Throttler_OneMinuteRate': 'kafka.utils.Throttler.OneMinuteRate',
}
AMAZON_MSK_JMX_METRICS_OVERRIDES = {
    'kafka_cluster_Partition_Value': 'gauge',
    'kafka_controller_ControllerChannelManager_50thPercentile': 'gauge',
    'kafka_controller_ControllerChannelManager_75thPercentile': 'gauge',
    'kafka_controller_ControllerChannelManager_95thPercentile': 'gauge',
    'kafka_controller_ControllerChannelManager_98thPercentile': 'gauge',
    'kafka_controller_ControllerChannelManager_999thPercentile': 'gauge',
    'kafka_controller_ControllerChannelManager_99thPercentile': 'gauge',
    'kafka_controller_ControllerChannelManager_Count': 'gauge',
    'kafka_controller_ControllerChannelManager_FifteenMinuteRate': 'gauge',
    'kafka_controller_ControllerChannelManager_FiveMinuteRate': 'gauge',
    'kafka_controller_ControllerChannelManager_Max': 'gauge',
    'kafka_controller_ControllerChannelManager_Mean': 'gauge',
    'kafka_controller_ControllerChannelManager_MeanRate': 'gauge',
    'kafka_controller_ControllerChannelManager_Min': 'gauge',
    'kafka_controller_ControllerChannelManager_OneMinuteRate': 'gauge',
    'kafka_controller_ControllerChannelManager_StdDev': 'gauge',
    'kafka_controller_ControllerChannelManager_Value': 'gauge',
    'kafka_controller_ControllerEventManager_50thPercentile': 'gauge',
    'kafka_controller_ControllerEventManager_75thPercentile': 'gauge',
    'kafka_controller_ControllerEventManager_95thPercentile': 'gauge',
    'kafka_controller_ControllerEventManager_98thPercentile': 'gauge',
    'kafka_controller_ControllerEventManager_999thPercentile': 'gauge',
    'kafka_controller_ControllerEventManager_99thPercentile': 'gauge',
    'kafka_controller_ControllerEventManager_Count': 'gauge',
    'kafka_controller_ControllerEventManager_Max': 'gauge',
    'kafka_controller_ControllerEventManager_Mean': 'gauge',
    'kafka_controller_ControllerEventManager_Min': 'gauge',
    'kafka_controller_ControllerEventManager_StdDev': 'gauge',
    'kafka_controller_ControllerEventManager_Value': 'gauge',
    'kafka_controller_ControllerStats_50thPercentile': 'gauge',
    'kafka_controller_ControllerStats_75thPercentile': 'gauge',
    'kafka_controller_ControllerStats_95thPercentile': 'gauge',
    'kafka_controller_ControllerStats_98thPercentile': 'gauge',
    'kafka_controller_ControllerStats_999thPercentile': 'gauge',
    'kafka_controller_ControllerStats_99thPercentile': 'gauge',
    'kafka_controller_ControllerStats_Count': 'gauge',
    'kafka_controller_ControllerStats_FifteenMinuteRate': 'gauge',
    'kafka_controller_ControllerStats_FiveMinuteRate': 'gauge',
    'kafka_controller_ControllerStats_Max': 'gauge',
    'kafka_controller_ControllerStats_Mean': 'gauge',
    'kafka_controller_ControllerStats_MeanRate': 'gauge',
    'kafka_controller_ControllerStats_Min': 'gauge',
    'kafka_controller_ControllerStats_OneMinuteRate': 'gauge',
    'kafka_controller_ControllerStats_StdDev': 'gauge',
    'kafka_controller_KafkaController_Value': 'gauge',
    'kafka_coordinator_group_GroupMetadataManager_Value': 'gauge',
    'kafka_coordinator_transaction_TransactionMarkerChannelManager_Value': 'gauge',
    'kafka_log_LogCleanerManager_Value': 'gauge',
    'kafka_log_LogCleaner_Value': 'gauge',
    'kafka_log_LogManager_Value': 'gauge',
    'kafka_log_Log_Value': 'gauge',
    'kafka_network_Acceptor_Count': 'gauge',
    'kafka_network_Acceptor_FifteenMinuteRate': 'gauge',
    'kafka_network_Acceptor_FiveMinuteRate': 'gauge',
    'kafka_network_Acceptor_MeanRate': 'gauge',
    'kafka_network_Acceptor_OneMinuteRate': 'gauge',
    'kafka_network_Processor_Value': 'gauge',
    'kafka_network_RequestChannel_Value': 'gauge',
    'kafka_network_RequestMetrics_50thPercentile': 'gauge',
    'kafka_network_RequestMetrics_75thPercentile': 'gauge',
    'kafka_network_RequestMetrics_95thPercentile': 'gauge',
    'kafka_network_RequestMetrics_98thPercentile': 'gauge',
    'kafka_network_RequestMetrics_999thPercentile': 'gauge',
    'kafka_network_RequestMetrics_99thPercentile': 'gauge',
    'kafka_network_RequestMetrics_Count': 'gauge',
    'kafka_network_RequestMetrics_FifteenMinuteRate': 'gauge',
    'kafka_network_RequestMetrics_FiveMinuteRate': 'gauge',
    'kafka_network_RequestMetrics_Max': 'gauge',
    'kafka_network_RequestMetrics_Mean': 'gauge',
    'kafka_network_RequestMetrics_MeanRate': 'gauge',
    'kafka_network_RequestMetrics_Min': 'gauge',
    'kafka_network_RequestMetrics_OneMinuteRate': 'gauge',
    'kafka_network_RequestMetrics_StdDev': 'gauge',
    'kafka_network_SocketServer_Value': 'gauge',
    'kafka_security_SimpleAclAuthorizer_Count': 'gauge',
    'kafka_security_SimpleAclAuthorizer_FifteenMinuteRate': 'gauge',
    'kafka_security_SimpleAclAuthorizer_FiveMinuteRate': 'gauge',
    'kafka_security_SimpleAclAuthorizer_MeanRate': 'gauge',
    'kafka_security_SimpleAclAuthorizer_OneMinuteRate': 'gauge',
    'kafka_server_BrokerTopicMetrics_Count': 'gauge',
    'kafka_server_BrokerTopicMetrics_FifteenMinuteRate': 'gauge',
    'kafka_server_BrokerTopicMetrics_FiveMinuteRate': 'gauge',
    'kafka_server_BrokerTopicMetrics_MeanRate': 'gauge',
    'kafka_server_BrokerTopicMetrics_OneMinuteRate': 'gauge',
    'kafka_server_DelayedFetchMetrics_Count': 'gauge',
    'kafka_server_DelayedFetchMetrics_FifteenMinuteRate': 'gauge',
    'kafka_server_DelayedFetchMetrics_FiveMinuteRate': 'gauge',
    'kafka_server_DelayedFetchMetrics_MeanRate': 'gauge',
    'kafka_server_DelayedFetchMetrics_OneMinuteRate': 'gauge',
    'kafka_server_DelayedOperationPurgatory_Value': 'gauge',
    'kafka_server_FetchSessionCache_Count': 'gauge',
    'kafka_server_FetchSessionCache_FifteenMinuteRate': 'gauge',
    'kafka_server_FetchSessionCache_FiveMinuteRate': 'gauge',
    'kafka_server_FetchSessionCache_MeanRate': 'gauge',
    'kafka_server_FetchSessionCache_OneMinuteRate': 'gauge',
    'kafka_server_FetchSessionCache_Value': 'gauge',
    'kafka_server_Fetch_queue_size': 'gauge',
    'kafka_server_FetcherLagMetrics_Value': 'gauge',
    'kafka_server_FetcherStats_Count': 'gauge',
    'kafka_server_FetcherStats_FifteenMinuteRate': 'gauge',
    'kafka_server_FetcherStats_FiveMinuteRate': 'gauge',
    'kafka_server_FetcherStats_MeanRate': 'gauge',
    'kafka_server_FetcherStats_OneMinuteRate': 'gauge',
    'kafka_server_KafkaRequestHandlerPool_Count': 'gauge',
    'kafka_server_KafkaRequestHandlerPool_FifteenMinuteRate': 'gauge',
    'kafka_server_KafkaRequestHandlerPool_FiveMinuteRate': 'gauge',
    'kafka_server_KafkaRequestHandlerPool_MeanRate': 'gauge',
    'kafka_server_KafkaRequestHandlerPool_OneMinuteRate': 'gauge',
    'kafka_server_KafkaServer_Value': 'gauge',
    'kafka_server_LeaderReplication_byte_rate': 'gauge',
    'kafka_server_Produce_queue_size': 'gauge',
    'kafka_server_ReplicaAlterLogDirsManager_Value': 'gauge',
    'kafka_server_ReplicaFetcherManager_Value': 'gauge',
    'kafka_server_ReplicaManager_Count': 'gauge',
    'kafka_server_ReplicaManager_FifteenMinuteRate': 'gauge',
    'kafka_server_ReplicaManager_FiveMinuteRate': 'gauge',
    'kafka_server_ReplicaManager_MeanRate': 'gauge',
    'kafka_server_ReplicaManager_OneMinuteRate': 'gauge',
    'kafka_server_ReplicaManager_Value': 'gauge',
    'kafka_server_Request_queue_size': 'gauge',
    'kafka_server_SessionExpireListener_Count': 'gauge',
    'kafka_server_SessionExpireListener_FifteenMinuteRate': 'gauge',
    'kafka_server_SessionExpireListener_FiveMinuteRate': 'gauge',
    'kafka_server_SessionExpireListener_MeanRate': 'gauge',
    'kafka_server_SessionExpireListener_OneMinuteRate': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_50thPercentile': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_75thPercentile': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_95thPercentile': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_98thPercentile': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_999thPercentile': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_99thPercentile': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_Count': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_Max': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_Mean': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_Min': 'gauge',
    'kafka_server_ZooKeeperClientMetrics_StdDev': 'gauge',
    'kafka_server_controller_channel_metrics_connection_close_rate': 'gauge',
    'kafka_server_controller_channel_metrics_connection_close_total': 'gauge',
    'kafka_server_controller_channel_metrics_connection_count': 'gauge',
    'kafka_server_controller_channel_metrics_connection_creation_rate': 'gauge',
    'kafka_server_controller_channel_metrics_connection_creation_total': 'gauge',
    'kafka_server_controller_channel_metrics_failed_authentication_rate': 'gauge',
    'kafka_server_controller_channel_metrics_failed_authentication_total': 'gauge',
    'kafka_server_controller_channel_metrics_failed_reauthentication_rate': 'gauge',
    'kafka_server_controller_channel_metrics_failed_reauthentication_total': 'gauge',
    'kafka_server_controller_channel_metrics_incoming_byte_rate': 'gauge',
    'kafka_server_controller_channel_metrics_incoming_byte_total': 'gauge',
    'kafka_server_controller_channel_metrics_io_ratio': 'gauge',
    'kafka_server_controller_channel_metrics_io_time_ns_avg': 'gauge',
    'kafka_server_controller_channel_metrics_io_wait_ratio': 'gauge',
    'kafka_server_controller_channel_metrics_io_wait_time_ns_avg': 'gauge',
    'kafka_server_controller_channel_metrics_io_waittime_total': 'gauge',
    'kafka_server_controller_channel_metrics_iotime_total': 'gauge',
    'kafka_server_controller_channel_metrics_network_io_rate': 'gauge',
    'kafka_server_controller_channel_metrics_network_io_total': 'gauge',
    'kafka_server_controller_channel_metrics_outgoing_byte_rate': 'gauge',
    'kafka_server_controller_channel_metrics_outgoing_byte_total': 'gauge',
    'kafka_server_controller_channel_metrics_reauthentication_latency_avg': 'gauge',
    'kafka_server_controller_channel_metrics_reauthentication_latency_max': 'gauge',
    'kafka_server_controller_channel_metrics_request_rate': 'gauge',
    'kafka_server_controller_channel_metrics_request_size_avg': 'gauge',
    'kafka_server_controller_channel_metrics_request_size_max': 'gauge',
    'kafka_server_controller_channel_metrics_request_total': 'gauge',
    'kafka_server_controller_channel_metrics_response_rate': 'gauge',
    'kafka_server_controller_channel_metrics_response_total': 'gauge',
    'kafka_server_controller_channel_metrics_select_rate': 'gauge',
    'kafka_server_controller_channel_metrics_select_total': 'gauge',
    'kafka_server_controller_channel_metrics_successful_authentication_no_reauth_total': 'gauge',
    'kafka_server_controller_channel_metrics_successful_authentication_rate': 'gauge',
    'kafka_server_controller_channel_metrics_successful_authentication_total': 'gauge',
    'kafka_server_controller_channel_metrics_successful_reauthentication_rate': 'gauge',
    'kafka_server_controller_channel_metrics_successful_reauthentication_total': 'gauge',
    'kafka_server_kafka_metrics_count_count': 'gauge',
    'kafka_server_replica_fetcher_metrics_connection_close_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_connection_close_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_connection_count': 'gauge',
    'kafka_server_replica_fetcher_metrics_connection_creation_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_connection_creation_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_failed_authentication_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_failed_authentication_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_incoming_byte_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_incoming_byte_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_io_ratio': 'gauge',
    'kafka_server_replica_fetcher_metrics_io_time_ns_avg': 'gauge',
    'kafka_server_replica_fetcher_metrics_io_wait_ratio': 'gauge',
    'kafka_server_replica_fetcher_metrics_io_wait_time_ns_avg': 'gauge',
    'kafka_server_replica_fetcher_metrics_io_waittime_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_iotime_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_network_io_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_network_io_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_outgoing_byte_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_outgoing_byte_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_request_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_request_size_avg': 'gauge',
    'kafka_server_replica_fetcher_metrics_request_size_max': 'gauge',
    'kafka_server_replica_fetcher_metrics_request_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_response_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_response_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_select_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_select_total': 'gauge',
    'kafka_server_replica_fetcher_metrics_successful_authentication_rate': 'gauge',
    'kafka_server_replica_fetcher_metrics_successful_authentication_total': 'gauge',
    'kafka_server_socket_server_metrics_MemoryPoolAvgDepletedPercent': 'gauge',
    'kafka_server_socket_server_metrics_MemoryPoolDepletedTimeTotal': 'gauge',
    'kafka_server_socket_server_metrics_connection_close_rate': 'gauge',
    'kafka_server_socket_server_metrics_connection_close_total': 'gauge',
    'kafka_server_socket_server_metrics_connection_count': 'gauge',
    'kafka_server_socket_server_metrics_connection_creation_rate': 'gauge',
    'kafka_server_socket_server_metrics_connection_creation_total': 'gauge',
    'kafka_server_socket_server_metrics_expired_connections_killed_count': 'gauge',
    'kafka_server_socket_server_metrics_failed_authentication_rate': 'gauge',
    'kafka_server_socket_server_metrics_failed_authentication_total': 'gauge',
    'kafka_server_socket_server_metrics_failed_reauthentication_rate': 'gauge',
    'kafka_server_socket_server_metrics_failed_reauthentication_total': 'gauge',
    'kafka_server_socket_server_metrics_incoming_byte_rate': 'gauge',
    'kafka_server_socket_server_metrics_incoming_byte_total': 'gauge',
    'kafka_server_socket_server_metrics_io_ratio': 'gauge',
    'kafka_server_socket_server_metrics_io_time_ns_avg': 'gauge',
    'kafka_server_socket_server_metrics_io_wait_ratio': 'gauge',
    'kafka_server_socket_server_metrics_io_wait_time_ns_avg': 'gauge',
    'kafka_server_socket_server_metrics_io_waittime_total': 'gauge',
    'kafka_server_socket_server_metrics_iotime_total': 'gauge',
    'kafka_server_socket_server_metrics_network_io_rate': 'gauge',
    'kafka_server_socket_server_metrics_network_io_total': 'gauge',
    'kafka_server_socket_server_metrics_outgoing_byte_rate': 'gauge',
    'kafka_server_socket_server_metrics_outgoing_byte_total': 'gauge',
    'kafka_server_socket_server_metrics_reauthentication_latency_avg': 'gauge',
    'kafka_server_socket_server_metrics_reauthentication_latency_max': 'gauge',
    'kafka_server_socket_server_metrics_request_rate': 'gauge',
    'kafka_server_socket_server_metrics_request_size_avg': 'gauge',
    'kafka_server_socket_server_metrics_request_size_max': 'gauge',
    'kafka_server_socket_server_metrics_request_total': 'gauge',
    'kafka_server_socket_server_metrics_response_rate': 'gauge',
    'kafka_server_socket_server_metrics_response_total': 'gauge',
    'kafka_server_socket_server_metrics_select_rate': 'gauge',
    'kafka_server_socket_server_metrics_select_total': 'gauge',
    'kafka_server_socket_server_metrics_successful_authentication_no_reauth_total': 'gauge',
    'kafka_server_socket_server_metrics_successful_authentication_rate': 'gauge',
    'kafka_server_socket_server_metrics_successful_authentication_total': 'gauge',
    'kafka_server_socket_server_metrics_successful_reauthentication_rate': 'gauge',
    'kafka_server_socket_server_metrics_successful_reauthentication_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_connection_close_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_connection_close_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_connection_count': 'gauge',
    'kafka_server_txn_marker_channel_metrics_connection_creation_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_connection_creation_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_failed_authentication_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_failed_authentication_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_failed_reauthentication_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_failed_reauthentication_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_incoming_byte_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_incoming_byte_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_io_ratio': 'gauge',
    'kafka_server_txn_marker_channel_metrics_io_time_ns_avg': 'gauge',
    'kafka_server_txn_marker_channel_metrics_io_wait_ratio': 'gauge',
    'kafka_server_txn_marker_channel_metrics_io_wait_time_ns_avg': 'gauge',
    'kafka_server_txn_marker_channel_metrics_io_waittime_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_iotime_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_network_io_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_network_io_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_outgoing_byte_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_outgoing_byte_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_reauthentication_latency_avg': 'gauge',
    'kafka_server_txn_marker_channel_metrics_reauthentication_latency_max': 'gauge',
    'kafka_server_txn_marker_channel_metrics_request_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_request_size_avg': 'gauge',
    'kafka_server_txn_marker_channel_metrics_request_size_max': 'gauge',
    'kafka_server_txn_marker_channel_metrics_request_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_response_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_response_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_select_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_select_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_successful_authentication_no_reauth_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_successful_authentication_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_successful_authentication_total': 'gauge',
    'kafka_server_txn_marker_channel_metrics_successful_reauthentication_rate': 'gauge',
    'kafka_server_txn_marker_channel_metrics_successful_reauthentication_total': 'gauge',
    'kafka_utils_Throttler_Count': 'gauge',
    'kafka_utils_Throttler_FifteenMinuteRate': 'gauge',
    'kafka_utils_Throttler_FiveMinuteRate': 'gauge',
    'kafka_utils_Throttler_MeanRate': 'gauge',
    'kafka_utils_Throttler_OneMinuteRate': 'gauge',
}
