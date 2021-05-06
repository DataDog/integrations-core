# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

import boto3

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper
from datadog_checks.base.utils.serialization import json

from .config_models import ConfigMixin
from .metrics import construct_jmx_metrics_config, construct_node_metrics_config


class AmazonMskCheckV2(OpenMetricsBaseCheckV2, ConfigMixin):
    __NAMESPACE__ = 'aws.msk'

    DEFAULT_METRIC_LIMIT = 0

    HTTP_CONFIG_REMAPPER = {'tls_verify': {'name': 'tls_verify', 'default': False}}

    SERVICE_CHECK_CONNECT = 'can_connect'

    def __init__(self, name, init_config, instances):
        super().__init__(name, init_config, instances)

        self._region_name = None
        self._exporter_data = None
        self._endpoint_prefix = None
        self._static_tags = None
        self._service_check_tags = None

        self.check_initializations.append(self.parse_config)

    def refresh_scrapers(self):
        # Create assume_role credentials if assume_role ARN is specified in config
        assume_role = self.config.assume_role
        if assume_role:
            self.log.info('Assume role %s found. Creating temporary credentials using role...', assume_role)
            sts = boto3.client('sts')
            response = sts.assume_role(
                RoleArn=assume_role, RoleSessionName='dd-msk-check-session', DurationSeconds=3600
            )
            access_key_id = response['Credentials']['AccessKeyId']
            secret_access_key = response['Credentials']['SecretAccessKey']
            session_token = response['Credentials']['SessionToken']
            client = boto3.client(
                'kafka',
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
                aws_session_token=session_token,
                region_name=self._region_name,
            )
        else:
            # Always create a new client to account for changes in auth
            client = boto3.client('kafka', region_name=self._region_name)

        try:
            response = client.list_nodes(ClusterArn=self.config.cluster_arn)
            self.log.debug('Received list_nodes response: %s', json.dumps(response))
        except Exception as e:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.CRITICAL, message=str(e), tags=self._service_check_tags)
            raise
        else:
            self.service_check(self.SERVICE_CHECK_CONNECT, self.OK, tags=self._service_check_tags)

        scrapers = {}

        for node_info in response['NodeInfoList']:
            broker_info = node_info['BrokerNodeInfo']
            broker_id_tag = f'broker_id:{broker_info["BrokerId"]}'

            for endpoint in broker_info['Endpoints']:
                for port, metrics in self._exporter_data:
                    url = f'{self._endpoint_prefix}://{endpoint}:{port}{self.config.prometheus_metrics_path}'
                    if url in self.scrapers:
                        scrapers[url] = self.scrapers[url]
                        continue

                    scraper = self.create_scraper({'openmetrics_endpoint': url, 'metrics': metrics, **self.instance})
                    scraper.static_tags += self._static_tags
                    scraper.set_dynamic_tags(broker_id_tag)

                    scrapers[url] = scraper

        self.scrapers = scrapers

    def parse_config(self):
        self._region_name = self.config.region_name
        if not self._region_name:
            self._region_name = self.config.cluster_arn.split(':')[3]
            self.log.info('No `region_name` was set, defaulting to `%s` based on the `cluster_arn`', self._region_name)

        self._static_tags = (f'cluster_arn:{self.config.cluster_arn}', f'region_name:{self._region_name}')
        self._service_check_tags = self._static_tags + self.config.tags

        self._endpoint_prefix = 'https' if self.config.tls_verify else 'http'
        self._exporter_data = (
            (self.config.jmx_exporter_port, construct_jmx_metrics_config()),
            (self.config.node_exporter_port, construct_node_metrics_config()),
        )

    def create_scraper(self, config):
        return OpenMetricsCompatibilityScraper(self, self.get_config_with_defaults(config))

    def get_config_with_defaults(self, config):
        return ChainMap(config, {'metrics': config.pop('metrics')})

    def configure_scrapers(self):
        # No need as we manually configure scrapers
        pass
