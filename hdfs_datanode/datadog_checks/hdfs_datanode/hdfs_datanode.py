# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

'''
HDFS DataNode Metrics
---------------------
hdfs.datanode.dfs_remaining                  The remaining disk space left in bytes
hdfs.datanode.dfs_capacity                   Disk capacity in bytes
hdfs.datanode.dfs_used                       Disk usage in bytes
hdfs.datanode.cache_capacity                 Cache capacity in bytes
hdfs.datanode.cache_used                     Cache used in bytes
hdfs.datanode.num_failed_volumes             Number of failed volumes
hdfs.datanode.last_volume_failure_date       Date the last volume failed
hdfs.datanode.estimated_capacity_lost_total  The estimated capacity lost in bytes
hdfs.datanode.num_blocks_cached              The number of blocks cached
hdfs.datanode.num_blocks_failed_to_cache     The number of blocks that failed to cache
hdfs.datanode.num_blocks_failed_to_uncache   The number of failed blocks to remove from cache
'''

# stdlib
from urlparse import urljoin

# 3rd party
import requests
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError
from simplejson import JSONDecodeError

# Project
from datadog_checks.checks import AgentCheck


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

        # Authenticate our connection to JMX endpoint if required
        username = instance.get('username')
        password = instance.get('password')
        auth = None
        if username is not None and password is not None:
            auth = (username, password)

        disable_ssl_validation = instance.get('disable_ssl_validation', False)

        # Get data from JMX
        hdfs_datanode_beans = self._get_jmx_data(jmx_address, auth, disable_ssl_validation, tags)

        # Process the JMX data and send out metrics
        if hdfs_datanode_beans:
            self._hdfs_datanode_metrics(hdfs_datanode_beans, tags)

    def _get_jmx_data(self, jmx_address, auth, disable_ssl_validation, tags):
        """
        Get namenode beans data from JMX endpoint
        """
        response = self._rest_request_to_json(
            jmx_address, auth, disable_ssl_validation, self.JMX_PATH, {'qry': self.HDFS_DATANODE_BEAN_NAME}, tags=tags
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

        for metric, (metric_name, metric_type) in self.HDFS_METRICS.iteritems():
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

    def _rest_request_to_json(self, address, auth, disable_ssl_validation, object_path, query_params, tags):
        """
        Query the given URL and return the JSON response
        """
        response_json = None

        url = address

        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add query_params as arguments
        if query_params:
            query = '&'.join(['{}={}'.format(key, value) for key, value in query_params.iteritems()])
            url = urljoin(url, '?' + query)

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

    def _join_url_dir(self, url, *args):
        """
        Join a URL with multiple directories
        """

        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url
