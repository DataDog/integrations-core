# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


"""
HDFS NameNode Metrics
---------------------
hdfs.namenode.capacity_total                    Total disk capacity in bytes
hdfs.namenode.capacity_used                     Disk usage in bytes
hdfs.namenode.capacity_remaining                Remaining disk space left in bytes
hdfs.namenode.total_load                        Total load on the file system
hdfs.namenode.fs_lock_queue_length              Lock queue length
hdfs.namenode.blocks_total                      Total number of blocks
hdfs.namenode.max_objects                       Maximum number of files HDFS supports
hdfs.namenode.files_total                       Total number of files
hdfs.namenode.pending_replication_blocks        Number of blocks pending replication
hdfs.namenode.under_replicated_blocks           Number of under replicated blocks
hdfs.namenode.scheduled_replication_blocks      Number of blocks scheduled for replication
hdfs.namenode.pending_deletion_blocks           Number of pending deletion blocks
hdfs.namenode.num_live_data_nodes               Total number of live data nodes
hdfs.namenode.num_dead_data_nodes               Total number of dead data nodes
hdfs.namenode.num_decom_live_data_nodes         Number of decommissioning live data nodes
hdfs.namenode.num_decom_dead_data_nodes         Number of decommissioning dead data nodes
hdfs.namenode.volume_failures_total             Total volume failures
hdfs.namenode.estimated_capacity_lost_total     Estimated capacity lost in bytes
hdfs.namenode.num_decommissioning_data_nodes    Number of decommissioning data nodes
hdfs.namenode.num_stale_data_nodes              Number of stale data nodes
hdfs.namenode.num_stale_storages                Number of stale storages
hdfs.namenode.missing_blocks                    Number of missing blocks
hdfs.namenode.corrupt_blocks                    Number of corrupt blocks
"""

# stdlib
from urlparse import urljoin

# 3rd party
import requests
from requests.exceptions import Timeout, HTTPError, InvalidURL, ConnectionError
from simplejson import JSONDecodeError

# Project
from datadog_checks.checks import AgentCheck


class HDFSNameNode(AgentCheck):
    # Service check names
    JMX_SERVICE_CHECK = 'hdfs.namenode.jmx.can_connect'

    # URL Paths
    JMX_PATH = 'jmx'

    # Namesystem state bean
    HDFS_NAME_SYSTEM_STATE_BEAN = 'Hadoop:service=NameNode,name=FSNamesystemState'

    # Namesystem bean
    HDFS_NAME_SYSTEM_BEAN = 'Hadoop:service=NameNode,name=FSNamesystem'

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

    def check(self, instance):
        jmx_address = instance.get('hdfs_namenode_jmx_uri')
        if jmx_address is None:
            raise Exception("The JMX URL must be specified in the instance configuration")

        # Set up tags
        tags = instance.get("tags", [])
        tags.append("namenode_url:{}".format(jmx_address))
        tags = list(set(tags))

        # Authenticate our connection to JMX endpoint if required
        username = instance.get('username')
        password = instance.get('password')
        auth = None
        if username is not None and password is not None:
            auth = (username, password)

        # Get data from JMX
        disable_ssl_validation = instance.get('disable_ssl_validation', False)
        hdfs_system_state_beans = self._get_jmx_data(
            jmx_address, auth, disable_ssl_validation, self.HDFS_NAME_SYSTEM_STATE_BEAN, tags
        )
        hdfs_system_beans = self._get_jmx_data(
            jmx_address, auth, disable_ssl_validation, self.HDFS_NAME_SYSTEM_BEAN, tags
        )

        # Process the JMX data and send out metrics
        if hdfs_system_state_beans:
            self._hdfs_namenode_metrics(hdfs_system_state_beans, self.HDFS_NAME_SYSTEM_STATE_METRICS, tags)

        if hdfs_system_beans:
            self._hdfs_namenode_metrics(hdfs_system_beans, self.HDFS_NAME_SYSTEM_METRICS, tags)

        # Send an OK service check
        self.service_check(
            self.JMX_SERVICE_CHECK,
            AgentCheck.OK,
            tags=tags,
            message="Connection to {} was successful".format(jmx_address),
        )

    def _get_jmx_data(self, jmx_address, auth, disable_ssl_validation, bean_name, tags):
        """
        Get namenode beans data from JMX endpoint
        """

        response = self._rest_request_to_json(
            jmx_address, auth, disable_ssl_validation, self.JMX_PATH, {"qry": bean_name}, tags=tags
        )
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

        for metric, (metric_name, metric_type) in metrics.iteritems():
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
            self.log.error('Metric type "{}" unknown'.format(metric_type))

    def _rest_request_to_json(self, address, auth, disable_ssl_validation, object_path, query_params, tags=None):
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
                message='JSON Parse failed: {}, {}'.format(url, e),
            )
            raise

        except ValueError as e:
            self.service_check(self.JMX_SERVICE_CHECK, AgentCheck.CRITICAL, tags=tags, message=str(e))
            raise

        return response_json

    def _join_url_dir(self, url, *args):
        """
        Join a URL with multiple directories
        """

        for path in args:
            url = url.rstrip('/') + '/'
            url = urljoin(url, path.lstrip('/'))

        return url
