# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from collections import ChainMap

import boto3

from datadog_checks.base import OpenMetricsBaseCheckV2
from datadog_checks.base.checks.openmetrics.v2.scraper import OpenMetricsCompatibilityScraper
from datadog_checks.base.utils.serialization import json

from .config_models import ConfigMixin
from .metrics import (
    JMX_METRICS_MAP,
    METRICS_AS_GAUGE_AND_COUNT,
    METRICS_WITH_NAME_AS_LABEL,
    construct_jmx_metrics_config,
    construct_node_metrics_config,
)
from .utils import construct_boto_config

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


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
        proxies = self.instance.get('proxy', init_config.get('proxy', datadog_agent.get_config('proxy')))
        try:
            self._boto_config = construct_boto_config(self.instance.get('boto_config', {}), proxies=proxies)
        except TypeError as e:
            self.log.debug("Got error when constructing Config object: %s", str(e))
            self.log.debug("Boto Config parameters: %s", self.instance.get('boto_config'))
            self._boto_config = None
        self.check_initializations.append(self.parse_config)

    def refresh_scrapers(self):
        # Create assume_role credentials if assume_role ARN is specified in config
        assume_role = self.config.assume_role
        try:
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
                    if port:
                        url = f'{self._endpoint_prefix}://{endpoint}:{port}{self.config.prometheus_metrics_path}'
                        if url in self.scrapers:
                            scrapers[url] = self.scrapers[url]
                            continue

                        self.log.debug("OpenMetricsV2 prometheus endpoint: %s", url)
                        scraper = self.create_scraper(
                            {'openmetrics_endpoint': url, 'metrics': metrics, **self.instance}
                        )
                        scraper.static_tags += self._static_tags
                        scraper.set_dynamic_tags(broker_id_tag)
                        self.configure_additional_transformers(scraper.metric_transformer.transformer_data)

                        scrapers[url] = scraper

        self.scrapers = scrapers

    def configure_transformer_with_metric_label(self, legacy_name, new_name, label_name):
        def transform(metric, sample_data, runtime_data):
            for sample, tags, hostname in sample_data:
                self._submit_both_gauge_and_count(legacy_name, sample.value, tags=tags, hostname=hostname)

                tag = sample.labels.pop(label_name)
                tags.remove('{}:{}'.format(label_name, tag))

                new_name_to_submit = '{}.{}'.format(new_name, tag)
                self._submit_both_gauge_and_count(new_name_to_submit, sample.value, tags=tags, hostname=hostname)

        return transform

    def configure_submission_as_gauge_and_count(self, raw_metric_name):
        dd_name = JMX_METRICS_MAP[raw_metric_name]

        def transform(_metric, sample_data, _runtime_data):
            for sample, tags, hostname in sample_data:
                self._submit_both_gauge_and_count(dd_name, sample.value, tags=tags, hostname=hostname)

        return transform

    def _submit_both_gauge_and_count(self, name, value, tags, hostname):
        self.gauge(name, value, tags=tags, hostname=hostname)
        self.monotonic_count(name + ".count", value, tags=tags, hostname=hostname)

    def configure_additional_transformers(self, transformer_data):
        for metric, data in METRICS_WITH_NAME_AS_LABEL.items():
            transformer_data[metric] = None, self.configure_transformer_with_metric_label(**data)
        for metric in METRICS_AS_GAUGE_AND_COUNT:
            transformer_data[metric] = None, self.configure_submission_as_gauge_and_count(metric)

    def parse_config(self):
        self._region_name = self.config.region_name
        if not self._region_name:
            self._region_name = self.config.cluster_arn.split(':')[3]
            self.log.info('No `region_name` was set, defaulting to `%s` based on the `cluster_arn`', self._region_name)

        self._static_tags = (f'cluster_arn:{self.config.cluster_arn}', f'region_name:{self._region_name}')
        self._service_check_tags = self._static_tags
        if self.config.tags:
            self._service_check_tags += self.config.tags

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
