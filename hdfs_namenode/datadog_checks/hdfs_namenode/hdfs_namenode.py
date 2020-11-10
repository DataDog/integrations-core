# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from __future__ import division

from requests.exceptions import ConnectionError, HTTPError, InvalidURL, Timeout
from simplejson import JSONDecodeError
from six import iteritems
from six.moves.urllib.parse import urljoin

from datadog_checks.base import AgentCheck


class HDFSNameNode(AgentCheck):
    HTTP_CONFIG_REMAPPER = {'disable_ssl_validation': {'name': 'tls_verify', 'default': False, 'invert': True}}

    # Service check names
    JMX_SERVICE_CHECK = 'hdfs.namenode.jmx.can_connect'

    # URL Paths
    JMX_PATH = 'jmx'

    # Namesystem state bean
    HDFS_NAME_SYSTEM_STATE_BEAN = 'Hadoop:service=NameNode,name=FSNamesystemState'

    # Namesystem bean
    HDFS_NAME_SYSTEM_BEAN = 'Hadoop:service=NameNode,name=FSNamesystem'

    # Namesystem info bean
    HDFS_NAME_SYSTEM_METADATA_BEAN = 'Hadoop:service=NameNode,name=NameNodeInfo'

    # Metric types
    GAUGE = 'gauge'

    # HDFS metrics
    HDFS_NAME_SYSTEM_STATE_METRICS = {
        'CapacityTotal': ('hdfs.namenode.capacity_total', GAUGE),
        'CapacityUsed': ('hdfs.namenode.capacity_used', GAUGE),
        'CapacityRemaining': ('hdfs.namenode.capacity_remaining', GAUGE),
        'TotalLoad': ('hdfs.namenode.total_load', GAUGE),
        'FsLockQueueLength': ('hdfs.namenode.fs_lock_queue_length', GAUGE),
        'BlocksTotal': ('hdfs.namenode.blocks_total', GAUGE),
        'MaxObjects': ('hdfs.namenode.max_objects', GAUGE),
        'FilesTotal': ('hdfs.namenode.files_total', GAUGE),
        'PendingReplicationBlocks': ('hdfs.namenode.pending_replication_blocks', GAUGE),
        'UnderReplicatedBlocks': ('hdfs.namenode.under_replicated_blocks', GAUGE),
        'ScheduledReplicationBlocks': ('hdfs.namenode.scheduled_replication_blocks', GAUGE),
        'PendingDeletionBlocks': ('hdfs.namenode.pending_deletion_blocks', GAUGE),
        'NumLiveDataNodes': ('hdfs.namenode.num_live_data_nodes', GAUGE),
        'NumDeadDataNodes': ('hdfs.namenode.num_dead_data_nodes', GAUGE),
        'NumDecomLiveDataNodes': ('hdfs.namenode.num_decom_live_data_nodes', GAUGE),
        'NumDecomDeadDataNodes': ('hdfs.namenode.num_decom_dead_data_nodes', GAUGE),
        'VolumeFailuresTotal': ('hdfs.namenode.volume_failures_total', GAUGE),
        'EstimatedCapacityLostTotal': ('hdfs.namenode.estimated_capacity_lost_total', GAUGE),
        'NumDecommissioningDataNodes': ('hdfs.namenode.num_decommissioning_data_nodes', GAUGE),
        'NumStaleDataNodes': ('hdfs.namenode.num_stale_data_nodes', GAUGE),
        'NumStaleStorages': ('hdfs.namenode.num_stale_storages', GAUGE),
    }

    HDFS_NAME_SYSTEM_METRICS = {
        'MissingBlocks': ('hdfs.namenode.missing_blocks', GAUGE),
        'CorruptBlocks': ('hdfs.namenode.corrupt_blocks', GAUGE),
    }

    def check(self, _):
        jmx_address = self.instance.get('hdfs_namenode_jmx_uri')
        if jmx_address is None:
            raise Exception("The JMX URL must be specified in the instance configuration")

        # Set up tags
        tags = self.instance.get("tags", [])
        tags.append("namenode_url:{}".format(jmx_address))
        tags = list(set(tags))

        hdfs_system_state_beans = self._get_jmx_data(jmx_address, self.HDFS_NAME_SYSTEM_STATE_BEAN, tags)
        hdfs_system_beans = self._get_jmx_data(jmx_address, self.HDFS_NAME_SYSTEM_BEAN, tags)
        hdfs_metadata_beans = self._get_jmx_data(jmx_address, self.HDFS_NAME_SYSTEM_METADATA_BEAN, tags)

        # Process the JMX data and send out metrics
        if hdfs_system_state_beans:
            self._hdfs_namenode_metrics(hdfs_system_state_beans, self.HDFS_NAME_SYSTEM_STATE_METRICS, tags)

        if hdfs_system_beans:
            self._hdfs_namenode_metrics(hdfs_system_beans, self.HDFS_NAME_SYSTEM_METRICS, tags)

        if hdfs_metadata_beans:
            self._collect_metadata(hdfs_metadata_beans)

        # Send an OK service check
        self.service_check(
            self.JMX_SERVICE_CHECK,
            AgentCheck.OK,
            tags=tags,
            message="Connection to {} was successful".format(jmx_address),
        )

    def _get_jmx_data(self, jmx_address, bean_name, tags):
        """
        Get namenode beans data from JMX endpoint
        """

        response = self._rest_request_to_json(jmx_address, self.JMX_PATH, {"qry": bean_name}, tags=tags)
        beans = response.get("beans", [])
        return beans

    def _hdfs_namenode_metrics(self, beans, metrics, tags):
        """
        Get HDFS namenode metrics from JMX
        """
        bean = next(iter(beans))
        bean_name = bean.get('name')

        if bean_name != bean_name:
            raise Exception("Unexpected bean name {}".format(bean_name))

        for metric, (metric_name, metric_type) in iteritems(metrics):
            metric_value = bean.get(metric)

            if metric_value is not None:
                self._set_metric(metric_name, metric_type, metric_value, tags)

        if 'CapacityUsed' in bean and 'CapacityTotal' in bean:
            self._set_metric(
                'hdfs.namenode.capacity_in_use',
                self.GAUGE,
                float(bean['CapacityUsed']) / float(bean['CapacityTotal']),
                tags,
            )

    def _set_metric(self, metric_name, metric_type, value, tags=None):
        """
        Set a metric
        """
        if metric_type == self.GAUGE:
            self.gauge(metric_name, value, tags=tags)
        else:
            self.log.error('Metric type "%s" unknown', metric_type)

    def _rest_request_to_json(self, url, object_path, query_params, tags=None):
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
                message='JSON Parse failed: {}, {}'.format(url, e),
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

        version = data.get('SoftwareVersion', None)

        if version is not None:
            self.set_metadata('version', version)
            self.log.debug('found hadoop version %s', version)
        else:
            self.log.warning('could not retrieve hadoop version information, this was data retrieved: %s', data)
