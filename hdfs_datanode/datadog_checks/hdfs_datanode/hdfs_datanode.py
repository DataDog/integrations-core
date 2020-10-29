# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
from simplejson import JSONDecodeError
from six import iteritems
from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck


class HDFSDataNode(AgentCheck):
    HTTP_CONFIG_REMAPPER = {'disable_ssl_validation': {'name': 'tls_verify', 'default': False, 'invert': True}}

    # Service check names
    JMX_SERVICE_CHECK = 'hdfs.datanode.jmx.can_connect'

    # URL Paths
    JMX_PATH = 'jmx'

    # Metric types
    GAUGE = 'gauge'

    # HDFS bean name
    HDFS_DATANODE_BEAN_NAME = 'Hadoop:service=DataNode,name=FSDatasetState*'
    HDFS_DATANODE_VERSION_NAME = 'Hadoop:service=DataNode,name=DataNodeInfo'

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

    def check(self, _):
        jmx_address = self.instance.get('hdfs_datanode_jmx_uri')

        if jmx_address is None:
            raise Exception("The JMX URL must be specified in the instance configuration")

        # Set up tags
        tags = self.instance.get('tags', [])
        tags.append("datanode_url:{}".format(jmx_address))
        tags = list(set(tags))

        # Get version info from JMX
        datanode_info = self._get_jmx_data(jmx_address, self.HDFS_DATANODE_VERSION_NAME, tags)
        if datanode_info:
            self._collect_metadata(datanode_info)

        # Get data from JMX
        hdfs_datanode_beans = self._get_jmx_data(jmx_address, self.HDFS_DATANODE_BEAN_NAME, tags)

        # Process the JMX data and send out metrics
        if hdfs_datanode_beans:
            self._hdfs_datanode_metrics(hdfs_datanode_beans, tags)

        self.service_check(
            self.JMX_SERVICE_CHECK,
            AgentCheck.OK,
            tags=tags,
            message="Connection to {} was successful".format(jmx_address),
        )

    def _get_jmx_data(self, jmx_address, bean_name, tags):
        """
        Get datanode beans data from JMX endpoint
        """
        response = self._rest_request_to_json(jmx_address, self.JMX_PATH, {'qry': bean_name}, tags=tags)
        beans = response.get('beans', [])
        return beans

    def _hdfs_datanode_metrics(self, beans, tags):
        """
        Process HDFS Datanode metrics from given beans
        """
        # Only get the first bean
        bean = next(iter(beans))
        bean_name = bean.get('name')

        self.log.debug("Bean name retrieved: %s", bean_name)

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
            self.log.error('Metric type "%s" unknown', metric_type)

    def _rest_request_to_json(self, url, object_path, query_params, tags):
        """
        Query the given URL and return the JSON response
        """
        if object_path:
            url = self._join_url_dir(url, object_path)

        # Add query_params as arguments
        if query_params:
            query = '&'.join(['{}={}'.format(key, value) for key, value in iteritems(query_params)])
            url = urljoin(url, '?' + query)

        self.log.debug('Attempting to connect to "%s"', url)

        try:
            response = self.http.get(url)
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
            return response_json

    @classmethod
    def _join_url_dir(cls, url, *args):
        """
        Join a URL with multiple directories
        """

        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url

    def _collect_metadata(self, value):
        # only get first info block
        data = next(iter(value), {})

        version = data.get('Version', None)

        if version is not None:
            self.set_metadata('version', version)
            self.log.debug('found hadoop version %s', version)
        else:
            self.log.warning('could not retrieve hadoop version information, this was data retrieved: %s', data)
