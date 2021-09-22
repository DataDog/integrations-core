# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json

import boto3
from six import PY2

from datadog_checks.base import ConfigurationError, OpenMetricsBaseCheck, is_affirmative

from .metrics import JMX_METRICS_MAP, JMX_METRICS_OVERRIDES, NODE_METRICS_MAP, NODE_METRICS_OVERRIDES
from .utils import construct_boto_config

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


class AmazonMskCheck(OpenMetricsBaseCheck):
    """
    This is a legacy implementation that will be removed at some point, refer to check.py for the new implementation.
    """

    SERVICE_CHECK_CONNECT = 'aws.msk.can_connect'
    DEFAULT_METRIC_LIMIT = 0

    def __new__(cls, name, init_config, instances):
        instance = instances[0]

        if is_affirmative(instance.get('use_openmetrics', False)):
            if PY2:
                raise ConfigurationError(
                    "Openmetrics on this integration is only available when using py3. "
                    "Check https://docs.datadoghq.com/agent/guide/agent-v6-python-3 "
                    "for more information"
                )
            # TODO: when we drop Python 2 move this import up top
            from .check import AmazonMskCheckV2

            return AmazonMskCheckV2(name, init_config, instances)
        else:
            return super(AmazonMskCheck, cls).__new__(cls)

    def __init__(self, name, init_config, instances):
        super(AmazonMskCheck, self).__init__(
            name,
            init_config,
            instances,
            default_instances={'aws.msk': {'ssl_verify': False}},
            default_namespace='aws.msk',
        )
        self._region_name = None
        self._cluster_arn = None
        self._assume_role = None
        self._exporter_data = (
            (int(self.instance.get('jmx_exporter_port', 11001)), JMX_METRICS_MAP, JMX_METRICS_OVERRIDES),
            (int(self.instance.get('node_exporter_port', 11002)), NODE_METRICS_MAP, NODE_METRICS_OVERRIDES),
        )
        self._prometheus_metrics_path = self.instance.get('prometheus_metrics_path', '/metrics')
        proxies = self.instance.get('proxy', init_config.get('proxy', datadog_agent.get_config('proxy')))
        try:
            self._boto_config = construct_boto_config(self.instance.get('boto_config', {}), proxies=proxies)
        except TypeError as e:
            self.log.debug("Got error when constructing Config object: %s", str(e))
            self.log.debug("Boto Config parameters: %s", self.instance.get('boto_config'))
            self._boto_config = None

        instance = self.instance.copy()
        instance['prometheus_url'] = 'necessary for scraper creation'

        self._scraper_config = self.create_scraper_configuration(instance)
        self._endpoint_prefix = 'https' if self._scraper_config['ssl_verify'] else 'http'

        self.check_initializations.append(self.parse_config)

    def check(self, _):
        # Create assume_role credentials if assume_role ARN is specified in config
        if self._assume_role:
            self.log.info('Assume role %s found. Creating temporary credentials using role...', self._assume_role)
            sts = boto3.client('sts')
            response = sts.assume_role(
                RoleArn=self._assume_role, RoleSessionName='dd-msk-check-session', DurationSeconds=3600
            )
            access_key_id = response['Credentials']['AccessKeyId']
            secret_access_key = response['Credentials']['SecretAccessKey']
            session_token = response['Credentials']['SessionToken']
            client = boto3.client(
                'kafka',
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
                config=self._boto_config,
                region_name=self._region_name,
            )
        else:
            # Always create a new client to account for changes in auth
            client = boto3.client(
                'kafka',
                config=self._boto_config,
                region_name=self._region_name,
            )

        try:
            response = client.list_nodes(ClusterArn=self._cluster_arn)
            self.log.debug('Received list_nodes response: %s', json.dumps(response))
        except Exception as e:
            self.service_check(
                self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=str(e), tags=self._scraper_config['custom_tags']
            )
            raise
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._scraper_config['custom_tags'])

        for node_info in response['NodeInfoList']:
            broker_info = node_info['BrokerNodeInfo']
            self._scraper_config['_metric_tags'] = ['broker_id:{}'.format(broker_info['BrokerId'])]

            for endpoint in broker_info['Endpoints']:
                for (port, metrics_mapper, type_overrides) in self._exporter_data:
                    self._scraper_config['prometheus_url'] = '{}://{}:{}{}'.format(
                        self._endpoint_prefix, endpoint, port, self._prometheus_metrics_path
                    )
                    self._scraper_config['metrics_mapper'] = metrics_mapper
                    self._scraper_config['type_overrides'] = type_overrides

                    self.process(self._scraper_config)

    def parse_config(self):
        cluster_arn = self.instance.get('cluster_arn')
        if not cluster_arn:
            raise ConfigurationError('A `cluster_arn` must be provided')

        # Allow `null` to use additional fallback mechanisms
        if 'region_name' in self.instance:
            region_name = self.instance['region_name']
        else:
            region_name = cluster_arn.split(':')[3]
            self.log.info('No `region_name` was set, defaulting to `%s` based on the `cluster_arn`', region_name)

        if 'assume_role' in self.instance:
            self._assume_role = self.instance['assume_role']

        # Make a new list to avoid a memory leak when there are multiple instances
        self._scraper_config['custom_tags'] = list(self._scraper_config['custom_tags'])

        self._cluster_arn = cluster_arn
        self._scraper_config['custom_tags'].append('cluster_arn:{}'.format(self._cluster_arn))

        self._region_name = region_name
        self._scraper_config['custom_tags'].append('region_name:{}'.format(self._region_name))

    def get_scraper_config(self, instance):
        # This validation is called during `__init__` but we don't need it
        pass
