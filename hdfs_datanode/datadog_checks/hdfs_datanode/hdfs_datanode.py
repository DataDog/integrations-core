# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

import requests
import requests_kerberos
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError
from simplejson import JSONDecodeError
from six import iteritems
from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck, is_affirmative

KERBEROS_STRATEGIES = {
    'required': requests_kerberos.REQUIRED,
    'optional': requests_kerberos.OPTIONAL,
    'disabled': requests_kerberos.DISABLED,
}


class HDFSDataNode(AgentCheck):

    # Service check names
    JMX_SERVICE_CHECK = 'hdfs.datanode.jmx.can_connect'

    # URL Paths
    JMX_PATH = 'jmx'

    # Metric types
    GAUGE = 'gauge'

    # HDFS bean name
    HDFS_DATANODE_BEAN_NAME = 'Hadoop:service=DataNode,name=FSDatasetState*'

    # HDFS metrics
    HDFS_METRICS = {
        'Remaining': ('hdfs.datanode.dfs_remaining', GAUGE),
        'Capacity': ('hdfs.datanode.dfs_capacity', GAUGE),
        'DfsUsed': ('hdfs.datanode.dfs_used', GAUGE),
        'CacheCapacity': ('hdfs.datanode.cache_capacity', GAUGE),
        'CacheUsed': ('hdfs.datanode.cache_used', GAUGE),
        'NumFailedVolumes': ('hdfs.datanode.num_failed_volumes', GAUGE),
        'LastVolumeFailureDate': ('hdfs.datanode.last_volume_failure_date', GAUGE),
        'EstimatedCapacityLostTotal': ('hdfs.datanode.estimated_capacity_lost_total', GAUGE),
        'NumBlocksCached': ('hdfs.datanode.num_blocks_cached', GAUGE),
        'NumBlocksFailedToCache': ('hdfs.datanode.num_blocks_failed_to_cache', GAUGE),
        'NumBlocksFailedToUnCache': ('hdfs.datanode.num_blocks_failed_to_uncache', GAUGE),
    }

    def check(self, instance):
        jmx_address = instance.get('hdfs_datanode_jmx_uri')

        if jmx_address is None:
            raise Exception("The JMX URL must be specified in the instance configuration")

        # Set up tags
        tags = instance.get('tags', [])
        tags.append("datanode_url:{}".format(jmx_address))
        tags = list(set(tags))

        # Get data from JMX
        hdfs_datanode_beans = self._get_jmx_data(instance, jmx_address, tags)

        # Process the JMX data and send out metrics
        if hdfs_datanode_beans:
            self._hdfs_datanode_metrics(hdfs_datanode_beans, tags)

    def _get_jmx_data(self, instance, jmx_address, tags):
        """
        Get namenode beans data from JMX endpoint
        """
        response = self._rest_request_to_json(
            instance, jmx_address, self.JMX_PATH, {'qry': self.HDFS_DATANODE_BEAN_NAME}, tags=tags
        )
        beans = response.get('beans', [])
        return beans

    def _hdfs_datanode_metrics(self, beans, tags):
        """
        Process HDFS Datanode metrics from given beans
        """
        # Only get the first bean
        bean = next(iter(beans))
        bean_name = bean.get('name')

        self.log.debug("Bean name retrieved: {}".format(bean_name))

        for metric, (metric_name, metric_type) in iteritems(self.HDFS_METRICS):
            metric_value = bean.get(metric)
            if metric_value is not None:
                self._set_metric(metric_name, metric_type, metric_value, tags)

    def _set_metric(self, metric_name, metric_type, value, tags=None):
        """
        Set a metric
        """
        if metric_type == self.GAUGE:
            self.gauge(metric_name, value, tags=tags)
        else:
            self.log.error('Metric type "{}" unknown'.format(metric_type))

    def _rest_request_to_json(self, instance, url, object_path, query_params, tags):
        """
        Query the given URL and return the JSON response
        """
        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add query_params as arguments
        if query_params:
            query = '&'.join(['{}={}'.format(key, value) for key, value in iteritems(query_params)])
            url = urljoin(url, '?' + query)

        auth = None

        # Authenticate our connection to JMX endpoint if required
        kerberos = instance.get('kerberos')
        username = instance.get('username')
        password = instance.get('password')
        if username is not None and password is not None:
            auth = (username, password)
        elif kerberos is not None:
            if kerberos not in KERBEROS_STRATEGIES:
                raise Exception('Invalid Kerberos strategy `{}`'.format(kerberos))

            auth = requests_kerberos.HTTPKerberosAuth(
                mutual_authentication=KERBEROS_STRATEGIES[kerberos],
                delegate=is_affirmative(instance.get('kerberos_delegate', False)),
                force_preemptive=is_affirmative(instance.get('kerberos_force_initiate', False)),
                hostname_override=instance.get('kerberos_hostname'),
                principal=instance.get('kerberos_principal'),
            )

        disable_ssl_validation = is_affirmative(instance.get('disable_ssl_validation', False))

        old_keytab_path = None
        if 'kerberos_keytab' in instance:
            old_keytab_path = os.getenv('KRB5_CLIENT_KTNAME')
            os.environ['KRB5_CLIENT_KTNAME'] = instance['kerberos_keytab']

        self.log.debug('Attempting to connect to "{}"'.format(url))

        try:
            response = requests.get(
                url, auth=auth, timeout=self.default_integration_http_timeout, verify=not disable_ssl_validation
            )
            response.raise_for_status()
            response_json = response.json()

        except Timeout as e:
            self.service_check(
                self.JMX_SERVICE_CHECK, AgentCheck.CRITICAL, tags=tags, message="Request timeout: {}, {}".format(url, e)
            )
            raise

        except (HTTPError, InvalidURL, ConnectionError) as e:
            self.service_check(
                self.JMX_SERVICE_CHECK, AgentCheck.CRITICAL, tags=tags, message="Request failed: {}, {}".format(url, e)
            )
            raise

        except JSONDecodeError as e:
            self.service_check(
                self.JMX_SERVICE_CHECK,
                AgentCheck.CRITICAL,
                tags=tags,
                message="JSON Parse failed: {}, {}".format(url, e),
            )
            raise

        except ValueError as e:
            self.service_check(self.JMX_SERVICE_CHECK, AgentCheck.CRITICAL, tags=tags, message=str(e))
            raise

        else:
            self.service_check(
                self.JMX_SERVICE_CHECK, AgentCheck.OK, tags=tags, message="Connection to {} was successful".format(url)
            )

            return response_json

        finally:
            if old_keytab_path is not None:
                os.environ['KRB5_CLIENT_KTNAME'] = old_keytab_path

    @classmethod
    def _join_url_dir(cls, url, *args):
        """
        Join a URL with multiple directories
        """

        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url
