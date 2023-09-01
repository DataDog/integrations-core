# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from datadog_checks.base.utils.common import total_time_to_temporal_percent
from datadog_checks.base.utils.constants import SECOND


class Resource:
    def __init__(self, name):
        self.name = name.replace('.', '_')

    def normalized_metric_name(self, metric):
        # https://www.ibm.com/support/pages/apar/IT39095
        if ' ' in metric:
            metric = metric.title().replace(' ', '')

        return metric.replace('-', '_')

    def full_metric_name(self, metric):
        return f'{self.name}.{self.normalized_metric_name(metric)}'

    def parse_tags(self, global_tags, metric_data):
        group = metric_data.pop('name')
        return [f'group:{group}', *global_tags]

    def submit(self, check, metric, value, tags):
        # Most metrics seem to be counters:
        # https://www.ibm.com/docs/en/app-connect/12.0?topic=performance-resource-statistics-data
        check.count(self.full_metric_name(metric), value, tags=tags)


class ConnectDirectResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-connect-direct
    """

    def parse_tags(self, global_tags, metric_data):
        tags = super().parse_tags(global_tags, metric_data)
        metric_data.pop('ConnectionDetails', None)
        return tags


class FTPResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-ftp
    """

    def parse_tags(self, global_tags, metric_data):
        tags = super().parse_tags(global_tags, metric_data)

        ftp_protocol = metric_data.pop('Protocol', '')
        if ftp_protocol:
            tags.append(f'ftp_protocol:{ftp_protocol}')

        return tags


class JDBCConnectionPoolsResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-jdbc-connection-pools
    """

    def parse_tags(self, global_tags, metric_data):
        tags = super().parse_tags(global_tags, metric_data)

        jdbc_provider = metric_data.pop('NameOfJDBCProvider', '')
        if jdbc_provider:
            tags.append(f'jdbc_provider:{jdbc_provider}')

        return tags

    def submit(self, check, metric, value, tags):
        if metric in ('ActualSizeOfPool', 'MaxDelayInMilliseconds', 'MaxSizeOfPool'):
            check.gauge(self.full_metric_name(metric), value, tags=tags)
        else:
            super().submit(check, metric, value, tags)


class JMSResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-jms
    """

    def submit(self, check, metric, value, tags):
        if metric in ('NumberOfOpenJMSConnections', 'NumberOfOpenJMSSessions'):
            check.gauge(self.full_metric_name(metric), value, tags=tags)
        else:
            super().submit(check, metric, value, tags)


class JVMResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-java-virtual-machine-jvm
    """

    def submit(self, check, metric, value, tags):
        if value == -1:
            return

        if metric == 'CumulativeGCTimeInSeconds':
            check.rate(self.full_metric_name('GCTime'), total_time_to_temporal_percent(value, scale=SECOND), tags=tags)
        elif metric.endswith('MemoryInMB'):
            check.gauge(self.full_metric_name(metric), value, tags=tags)
        else:
            super().submit(check, metric, value, tags)


class MQTTResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-mqtt
    """

    def submit(self, check, metric, value, tags):
        if metric == 'OpenConnections':
            check.gauge(self.full_metric_name(metric), value, tags=tags)
        else:
            super().submit(check, metric, value, tags)


class NodeJSResource(Resource):
    def __init__(self, name):
        super().__init__('NodeJS')

    def submit(self, check, metric, value, tags):
        check.gauge(self.full_metric_name(metric), value, tags=tags)


class ODBCResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-odbc
    """

    def submit(self, check, metric, value, tags):
        if metric == 'ActiveConnections':
            check.gauge(self.full_metric_name(metric), value, tags=tags)
        else:
            super().submit(check, metric, value, tags)


class ParsersResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-parsers
    """

    def submit(self, check, metric, value, tags):
        if metric in ('ApproxMemKB', 'Fields', 'MaxReadKB', 'MaxWrittenKB', 'Threads'):
            check.gauge(self.full_metric_name(metric), value, tags=tags)
        else:
            super().submit(check, metric, value, tags)


class SOAPInputResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-soap-input
    """

    def parse_tags(self, global_tags, metric_data):
        tags = super().parse_tags(global_tags, metric_data)

        soap_policy_set = metric_data.pop('PolicySetApplied', '')
        if soap_policy_set:
            tags.append(f'soap_policy_set:{soap_policy_set}')

        return tags


class TCPIPClientNodesResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-tcpip-client-nodes
    """

    def submit(self, check, metric, value, tags):
        if metric == 'OpenConnections':
            check.gauge(self.full_metric_name(metric), value, tags=tags)
        else:
            super().submit(check, metric, value, tags)


class TCPIPServerNodesResource(Resource):
    """
    https://www.ibm.com/docs/en/app-connect/12.0?topic=data-tcpip-server-nodes
    """

    def submit(self, check, metric, value, tags):
        if metric == 'OpenConnections':
            check.gauge(self.full_metric_name(metric), value, tags=tags)
        else:
            super().submit(check, metric, value, tags)


RESOURCES = {
    'ConnectDirect': ConnectDirectResource,
    'FTP': FTPResource,
    'JDBCConnectionPools': JDBCConnectionPoolsResource,
    'JMS': JMSResource,
    'JVM': JVMResource,
    'MQTT': MQTTResource,
    'Node.js': NodeJSResource,
    'ODBC': ODBCResource,
    'Parsers': ParsersResource,
    'SOAPInput': SOAPInputResource,
    'TCPIPClientNodes': TCPIPClientNodesResource,
    'TCPIPServerNodes': TCPIPServerNodesResource,
}


def get_resource(name):
    return RESOURCES.get(name, Resource)(name)
