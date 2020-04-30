# (C) Datadog, Inc. 2010-2017
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import unicode_literals
from datetime import timedelta
from Queue import Empty, Queue
import re
import ssl
import time
import traceback
from collections import defaultdict
from datetime import datetime
import uuid

from pyVim import connect
from pyVmomi import vim  # pylint: disable=E0611
from pyVmomi import vmodl

from datadog_checks.config import _is_affirmative
from datadog_checks.checks import AgentCheck
from datadog_checks.checks.libs.vmware.basic_metrics import BASIC_METRICS
from datadog_checks.checks.libs.vmware.all_metrics import ALL_METRICS
from datadog_checks.checks.libs.thread_pool import Pool
from datadog_checks.checks.libs.timer import Timer
from .common import SOURCE_TYPE
from .event import VSphereEvent
from .metrics import ALLOWED_METRICS_FOR_MOR

from datadog import initialize,statsd

try:
    # Agent >= 6.0: the check pushes tags invoking `set_external_tags`
    from datadog_agent import set_external_tags
except ImportError:
    # Agent < 6.0: the Agent pulls tags invoking `VSphereCheck.get_external_host_tags`
    set_external_tags = None


# Default vCenter sampling interval
REAL_TIME_INTERVAL = 20
# Metrics are only collected on vSphere VMs marked by custom field value
VM_MONITORING_FLAG = 'DatadogMonitored'
# The size of the ThreadPool used to process the request queue
DEFAULT_SIZE_POOL = 4
# The interval in seconds between two refresh of the entities list
REFRESH_MORLIST_INTERVAL = 3 * 60
# The interval in seconds between two refresh of metrics metadata (id<->name)
REFRESH_METRICS_METADATA_INTERVAL = 10 * 60
# The amount of jobs batched at the same time in the queue to query available metrics
BATCH_MORLIST_SIZE = 50
# Maximum number of objects to collect at once by the propertyCollector. The size of the response returned by the query
# is significantly lower than the size of the queryPerf response, so allow specifying a different value.
BATCH_COLLECTOR_SIZE = 500

DEFAULT_METRICS_PER_QUERY = 500
DEFAULT_MAX_QUERY_METRICS = 64
# the vcenter maxquerymetrics option
MAX_QUERY_METRICS_OPTION = "config.vpxd.stats.maxQueryMetrics"


REALTIME_RESOURCES = [vim.VirtualMachine, vim.HostSystem]
HISTORICAL_RESOURCES = [vim.Datastore, vim.ClusterComputeResource]
ALL_RESOURCES_WITH_METRICS = REALTIME_RESOURCES + HISTORICAL_RESOURCES
ALL_RESOURCES_WITH_NO_METRICS = [vim.Folder,vim.Datacenter]

# Time after which we reap the jobs that clog the queue
# TODO: use it
JOB_TIMEOUT = 10
MORLIST = 'morlist'
METRICS_METADATA = 'metrics_metadata'
LAST = 'last'
INTERVAL = 'interval'
ERR_CODE = 'code'
ERR_MSG = 'msg'

#statsd config default values
STATSD_SERVER_HOST = '127.0.0.1'
STATSD_SERVER_PORT = 9000

def atomic_method(method):
    """ Decorator to catch the exceptions that happen in detached thread atomic tasks
    and display them in the logs.
    """
    def wrapper(*args, **kwargs):
        try:
            method(*args, **kwargs)
        except Exception:
            args[0].exceptionq.put("A worker thread crashed:\n" + traceback.format_exc())
    return wrapper


class VSphereCheck(AgentCheck):
    """ Get performance metrics from a vCenter server and upload them to Datadog
    References:
        http://pubs.vmware.com/vsphere-51/index.jsp#com.vmware.wssdk.apiref.doc/vim.PerformanceManager.html

    *_atomic jobs perform one single task asynchronously in the ThreadPool, we
    don't know exactly when they will finish, but we reap them if they're stuck.
    The other calls are performed synchronously.
    """

    SERVICE_CHECK_NAME = 'vcenter.can_connect'

    def __init__(self, name, init_config, agentConfig, instances):
        AgentCheck.__init__(self, name, init_config, agentConfig, instances)
        self.time_started = time.time()
        self.pool_started = False
        self.jobs_status = {}
        self.exceptionq = Queue()

        # Connections open to vCenter instances
        self.server_instances = {}

        # Event configuration
        self.event_config = {}
        # Batch size for property collector
        self.batch_collector_size = init_config.get("batch_property_collector_size", BATCH_COLLECTOR_SIZE)

        # Batch size for query available metrics
        self.batch_morlist_size = init_config.get('batch_morlist_size', BATCH_MORLIST_SIZE)

        # Metrics Query size
        self.max_historical_metrics = init_config.get("max_historical_metrics", DEFAULT_MAX_QUERY_METRICS)
        self.metrics_per_query = init_config.get("metrics_per_query", DEFAULT_METRICS_PER_QUERY)

        # Vcenter configuration cluster name list
        self.cluster_list = {}
        # cluster mors based on cluster name list to be monitored
        self.monitor_cluster_mors = {}

        # uuid cache
        self.cache_uuids = {}

        # error config
        self.error_configs = {}

        # Caching resources, timeouts
        self.cache_times = {}
        for instance in self.instances:
            i_key = self._instance_key(instance)
            self.cache_times[i_key] = {
                MORLIST: {
                    LAST: 0,
                    INTERVAL: init_config.get('refresh_morlist_interval',
                                              REFRESH_MORLIST_INTERVAL)
                },
                METRICS_METADATA: {
                    LAST: 0,
                    INTERVAL: init_config.get('refresh_metrics_metadata_interval',
                                              REFRESH_METRICS_METADATA_INTERVAL)
                }
            }

            self.event_config[i_key] = instance.get('event_config')
            self.cluster_list[i_key] = instance.get('cluster_list',[])
            self.cache_uuids[i_key] = {}
            for vimtype in HISTORICAL_RESOURCES:
                self.cache_uuids[i_key][vimtype] = {}
            self.error_configs[i_key] = {
                    ERR_CODE : None,
                    ERR_MSG : None
            }

        # managed entity raw view
        self.registry = {}
        # First layer of cache (get entities from the tree)
        self.morlist_raw = {}
        # Second layer, processed from the first one
        self.morlist = {}
        # Metrics metadata, basically perfCounterId -> {name, group, description}
        self.metrics_metadata = {}
        self.metric_ids = {}
        self.latest_event_query = {}

        #init the statsd client
        statsd_host = init_config.get('statsd_server_host',STATSD_SERVER_HOST)
        statsd_port = init_config.get('statsd_server_port',STATSD_SERVER_PORT)
        initialize(statsd_host = statsd_host, statsd_port = statsd_port)

    def stop(self):
        self.stop_pool()

    def start_pool(self):
        self.log.info("Starting Thread Pool")
        self.pool_size = int(self.init_config.get('threads_count', DEFAULT_SIZE_POOL))

        self.pool = Pool(self.pool_size)
        self.pool_started = True
        self.jobs_status = {}

    def stop_pool(self):
        self.log.info("Stopping Thread Pool")
        if self.pool_started:
            self.pool.terminate()
            self.pool.join()
            self.jobs_status.clear()
            assert self.pool.get_nworkers() == 0
            self.pool_started = False

    def restart_pool(self):
        self.stop_pool()
        self.start_pool()

    def _clean(self):
        now = time.time()
        # TODO: use that
        for name in self.jobs_status.keys():
            start_time = self.jobs_status[name]
            if now - start_time > JOB_TIMEOUT:
                self.log.critical("Restarting Pool. One check is stuck.")
                self.restart_pool()
                break

    def raiseAlert(self,instance,error_code,error_msg):
        if error_code == 'InvalidLogin':
            title = 'NTNX_NC_VC_user_authentication_alert'
        elif error_code == 'RuntimeFault':
                title = 'NTNX_NC_VC_server_not_reachable'
        else:
            title = None

        if title:
            text = error_msg
            alert_type = 'error'
            tags = []
            tags.append('vcenter_host:%s' % instance.get('host'))
            tags.append('vcenter_user:%s' % instance.get('username'))
            self.log.debug(u"Alert info. title:%s , text:%s , type:%s , tags:%s",title,text,alert_type,tags)
            statsd.event(title = title, text = text, alert_type = alert_type, tags = tags)

    def _query_event(self, instance):
        i_key = self._instance_key(instance)
        last_time = self.latest_event_query.get(i_key)

        server_instance = self._get_server_instance(instance)
        event_manager = server_instance.content.eventManager

        # Be sure we don't duplicate any event, never query the "past"
        if not last_time:
            last_time = event_manager.latestEvent.createdTime + timedelta(seconds=1)
            self.latest_event_query[i_key] = last_time

        query_filter = vim.event.EventFilterSpec()
        time_filter = vim.event.EventFilterSpec.ByTime(beginTime=last_time)
        query_filter.time = time_filter

        try:
            new_events = event_manager.QueryEvents(query_filter)
            self.log.debug("Got {0} events from vCenter event manager".format(len(new_events)))
            for event in new_events:
                normalized_event = VSphereEvent(event, self.event_config[i_key])
                # Can return None if the event if filtered out
                event_payload = normalized_event.get_datadog_payload()
                if event_payload is not None:
                    self.event(event_payload)
                last_time = event.createdTime + timedelta(seconds=1)
        except Exception as e:
            # Don't get stuck on a failure to fetch an event
            # Ignore them for next pass
            self.log.warning("Unable to fetch Events %s", e)
            last_time = event_manager.latestEvent.createdTime + timedelta(seconds=1)

        self.latest_event_query[i_key] = last_time

    def _instance_key(self, instance):
        i_key = instance.get('name')
        if i_key is None:
            raise Exception("Must define a unique 'name' per vCenter instance")
        return i_key

    def _should_cache(self, instance, entity):
        i_key = self._instance_key(instance)
        now = time.time()
        return now - self.cache_times[i_key][entity][LAST] > self.cache_times[i_key][entity][INTERVAL]

    def _get_server_instance(self, instance):
        i_key = self._instance_key(instance)
        error_config = self.error_configs.get(i_key)

        service_check_tags = [
            'vcenter_server:{0}'.format(instance.get('name')),
            'vcenter_host:{0}'.format(instance.get('host')),
        ]

        # Check for ssl configs and generate an appropriate ssl context object
        ssl_verify = instance.get('ssl_verify', True)
        ssl_capath = instance.get('ssl_capath', None)
        if not ssl_verify:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_NONE
        elif ssl_capath:
            context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_verify_locations(capath=ssl_capath)

        # If both configs are used, log a message explaining the default
        if not ssl_verify and ssl_capath:
            self.log.debug("Your configuration is incorrectly attempting to "
                           "specify both a CA path, and to disable SSL "
                           "verification. You cannot do both. Proceeding with "
                           "disabling ssl verification.")

        if i_key not in self.server_instances:
            try:
                # Object returned by SmartConnect is a ServerInstance
                #   https://www.vmware.com/support/developer/vc-sdk/visdk2xpubs/ReferenceGuide/vim.ServiceInstance.html
                server_instance = connect.SmartConnect(
                    host=instance.get('host'),
                    user=instance.get('username'),
                    pwd=instance.get('password'),
                    sslContext=context if not ssl_verify or ssl_capath else None
                )

            except vim.fault.InvalidLogin , e:
                err_msg = u"Invalid login credentials to %s , %s" % (instance.get('host'), str(e.msg))
                error_config.update({ERR_CODE : 'InvalidLogin'})
                error_config.update({ERR_MSG : err_msg})
                self.log.error(err_msg)

            except AttributeError , e:
                err_msg = u"Invalid configuration parameters : %s" % str(e)
                error_config.update({ERR_CODE : 'AttributeError'})
                error_config.update({ERR_MSG : err_msg})
                self.log.error(err_msg)

            except Exception as e:
                err_msg = "Connection to %s failed: %s" % (instance.get('host'), e)
                error_config.update({ERR_CODE : 'RuntimeFault'})
                error_config.update({ERR_MSG : err_msg})
                self.log.error(err_msg)
                self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                   tags=service_check_tags, message=err_msg)

            else:
                # Test if the connection is working
                try:
                    server_instance.RetrieveContent()
                    self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.OK,
                                       tags=service_check_tags)
                except Exception as e:
                    err_msg = "Connection to %s died unexpectedly: %s" % (instance.get('host'), e)
                    error_config.update({ERR_CODE : 'RuntimeFault'})
                    error_config.update({ERR_MSG : err_msg})
                    self.log.error(err_msg)
                    self.service_check(self.SERVICE_CHECK_NAME, AgentCheck.CRITICAL,
                                       tags=service_check_tags, message=err_msg)
                else:
                    self.server_instances[i_key] = server_instance

            #extract the error config to raise alarms for vcenter errors if any
            error_msg = error_config.get(ERR_MSG)
            error_code = error_config.get(ERR_CODE)
            if error_msg and error_code:
                self.raiseAlert(instance, error_code, error_msg)
                raise Exception(error_msg)

        return self.server_instances[i_key]

    def get_external_host_tags(self):
        """
        Returns a list of tags for every host that is detected by the vSphere
        integration.

        Returns a list of pairs (hostname, {'SOURCE_TYPE: list_of_tags},)
        """
        self.log.debug(u"Sending external_host_tags now")
        external_host_tags = []
        for instance in self.instances:
            i_key = self._instance_key(instance)
            for resource_type in ALL_RESOURCES_WITH_METRICS:
                mor_by_mor_name = self.morlist.get(i_key,{}).get(resource_type,{})

                if not mor_by_mor_name:
                    self.log.warning(
                        u"Unable to extract hosts' tags for vSphere instance named %s"
                        u"Is the check failing on this instance?", i_key
                    )
                    continue

                for mor in mor_by_mor_name.itervalues():
                    if mor['hostname']:  # some mor's have a None hostname
                        external_host_tags.append((mor['hostname'], {SOURCE_TYPE: mor['tags']}))

        return external_host_tags

    def getClusters(self,instance):
        server_instance = self._get_server_instance(instance)
        content = server_instance.content
        viewType = [vim.ClusterComputeResource]  # object types to look for
        view_ref = content.viewManager.CreateContainerView(content.rootFolder, viewType, True)

        collector = content.propertyCollector

        # Specify the root object from where we collect the rest of the objects
        obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.obj = view_ref
        obj_spec.skip = True

        # Specify the attribute of the root object to traverse to obtain all the attributes
        traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.path = "view"
        traversal_spec.skip = False
        traversal_spec.type = view_ref.__class__
        obj_spec.selectSet = [traversal_spec]

        property_spec = vmodl.query.PropertyCollector.PropertySpec()
        property_spec.type = vim.ClusterComputeResource
        property_spec.pathSet = ["name"]

        # Create our filter spec from the above specs
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = [obj_spec]
        filter_spec.propSet = [property_spec]
        filter_spec.reportMissingObjectsInResults = True

        retr_opts = self.createPropertyOptions()

        cluster_mors = {}
        i_key = self._instance_key(instance)
        error_config = self.error_configs[i_key]
        # Collect the objects and their properties
        try:
            res = collector.RetrievePropertiesEx([filter_spec], retr_opts)
            objects = res.objects
            # Results can be paginated
            while res.token is not None:
                res = collector.ContinueRetrievePropertiesEx(res.token)
                objects.extend(res.objects)

        except vmodl.query.InvalidProperty, e:
            err_msg = u"InvalidProperty fault while retrieving cluster properties : %s , %s" % (e.name, str(e.faultMessage))
            error_config.update(code = 'InvalidProperty')
            error_config.update(msg = err_msg)
            self.log.warning(err_msg)

        except vmodl.fault.InvalidArgument:
            err_msg = u"InvalidArgument fault while retrieving cluster properties : %s , %s" % (str(e.invalidProperty), str(e.faultMessage))
            error_config.update(code = 'InvalidArgument')
            error_config.update(msg = err_msg)
            self.log.warning(err_msg)

        except vmodl.fault.InvalidType:
            err_msg = u"InvalidType fault while retrieving cluster properties : %s , %s" % (str(e.argument),str(e.faultMessage))
            error_config.update(code = 'InvalidType')
            error_config.update(msg = err_msg)
            self.log.warning(err_msg)

        except vmodl.RuntimeFault, e:
            err_msg = u"Runtime fault while retrieving cluster properties : %s , %s" % (str(e.faultCause),str(e.faultMessage))
            error_config.update(code = 'RuntimeFault')
            error_config.update(msg = err_msg)
            self.log.warning(err_msg)

        else:
            for obj in objects:
                if obj.missingSet:
                    for prop in obj.missingSet:
                        self.log.warning(
                            u"Unable to retrieve property %s for object %s: %s",
                                                prop.path,str(obj.obj),str(prop.fault))

                if obj.propSet:
                    properties = {}
                    for prop in obj.propSet:
                        properties.update({prop.name : prop.val})

                    cluster_name = properties.get("name")
                    self.log.debug(u"Discovered cluster : %s",cluster_name)
                    if cluster_name:
                        cluster_mors[cluster_name] = obj.obj

        return cluster_mors

    def addClusterUuid(self,instance,cluster_name):
        i_key = self._instance_key(instance)
        cluster_cache = self.cache_uuids[i_key].get(vim.ClusterComputeResource)
        if cluster_name:
            cluster_uuid = cluster_cache.get(cluster_name,None)
            if cluster_uuid is None:
                try:
                    cluster_name_bytes = cluster_name.encode('utf-8')
                    cluster_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, cluster_name_bytes))
                    cluster_cache.update({cluster_name : cluster_uuid})
                    self.log.debug(u"Added uuid : %s for cluster : %s",cluster_uuid,cluster_name)
                except UnicodeError:
                    self.log.warning(u"Unable to generate uuid for cluster %s",cluster_name)
                    pass
            else:
                self.log.debug(u"uuid already added for cluster %s",cluster_name)
        else:
            self.log.warning(u"unable to add uuid for empty cluster name")

    def getClustersToMonitor(self,instance):
        i_key = self._instance_key(instance)
        error_config = self.error_configs[i_key]
        monitor_clusters = []
        i_key = self._instance_key(instance)
        if i_key not in self.monitor_cluster_mors:
            vcenter_clusters = self.cluster_list[i_key]
            if vcenter_clusters:
                self.log.info(u"Vcenter Cluster list : %s",vcenter_clusters)
                cluster_mors = self.getClusters(instance)
                if cluster_mors:
                    self.log.info(u"Completed enumeration of clusters for vcenter instance %s" % i_key)
                    for vcenter_cluster in vcenter_clusters:
                        cluster_mor = cluster_mors.get(vcenter_cluster)
                        if cluster_mor:
                            monitor_clusters.append(cluster_mor)
                            self.addClusterUuid(instance,vcenter_cluster)
                        else:
                            self.log.warning("Invalid cluster name %s",vcenter_cluster)

                    if not monitor_clusters:
                        error_msg = u"Invalid cluster list in vcenter configuration"
                        self.log.error(error_msg)
                        error_config.update({ERR_MSG : error_msg})
                        error_config.update({ERR_CODE : None})
                else:
                    self.log.error(u"Discovery of clusters failed.")
                    error_msg = error_config.get(ERR_MSG)
                    error_msg = u"Discovery of clusters failed due to %s" % error_msg
                    error_config.update({ERR_MSG : error_msg})
            else:
                error_msg = u"Empty cluster list in vcenter configuration"
                self.log.error(error_msg)
                error_config.update({ERR_MSG : error_msg})
                error_config.update({ERR_CODE : None})
            #update the cluster monitor list
            self.monitor_cluster_mors[i_key] = monitor_clusters
        else:
            monitor_clusters = self.monitor_cluster_mors[i_key]

        return monitor_clusters

    def createPropertyOptions(self):
            retr_opts = vmodl.query.PropertyCollector.RetrieveOptions()
            # To limit the number of objects retrieved per call.
            # If batch_collector_size is 0, collect maximum number of objects.
            retr_opts.maxObjects = self.batch_collector_size or None
            return retr_opts

    def _discover_mor(self, instance, tags, regexes=None, include_only_marked=False):
        """
        Explore vCenter infrastructure to discover hosts, virtual machines
        and compute their associated tags.


        Start with the vCenter `rootFolder` and proceed recursively,
        queueing other such jobs for children nodes.

        Example topology:
            ```
            rootFolder
                - datacenter1
                    - compute_resource1 == cluster
                        - host1
                        - host2
                        - host3
                    - compute_resource2
                        - host5
                            - vm1
                            - vm2
            ```

        If it's a node we want to query metric for, queue it in `self.morlist_raw` that
        will be processed by another job.
        """
        def _get_parent_tags(mor,all_mors):
            properties = all_mors.get(mor, {})
            parent = properties.get('parent')
            parent_mor = all_mors.get(parent, {})
            if parent and parent_mor:
                tags = []
                parent_name = parent_mor.get('name', 'unknown')
                if isinstance(parent, vim.HostSystem):
                    tags.append(u'vsphere_host:{}'.format(parent_name))
                elif isinstance(parent, vim.Folder):
                    tags.append(u'vsphere_folder:{}'.format(parent_name))
                elif isinstance(parent, vim.ComputeResource):
                    if isinstance(parent, vim.ClusterComputeResource):
                        tags.append(u'vsphere_cluster:{}'.format(parent_name))
                    tags.append(u'vsphere_compute:{}'.format(parent_name))
                elif isinstance(parent, vim.Datacenter):
                    tags.append(u'vsphere_datacenter:{}'.format(parent_name))

                parent_tags = _get_parent_tags(parent, all_mors)
                parent_tags.extend(tags)
                return parent_tags

            return []

        def createObjectSpecs(clusters):
            #Create list of cluster based object specification to define the starting point of navigation
            obj_specs = []
            for cluster in clusters:
                obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
                obj_spec.obj = cluster
                obj_spec.skip = False

                #Create a hierarchy based traversal specification to identify the path for collection
                host2VmTraversal = vmodl.query.PropertyCollector.TraversalSpec()
                host2VmTraversal.type = vim.HostSystem
                host2VmTraversal.path = 'vm'
                host2VmTraversal.skip = False
                host2VmTraversal.name = 'host2VmTraversal'

                cluster2HostTraversal = vmodl.query.PropertyCollector.TraversalSpec()
                cluster2HostTraversal.type = vim.ClusterComputeResource
                cluster2HostTraversal.path = 'host'
                cluster2HostTraversal.skip = False
                cluster2HostTraversal.name = 'cluster2HostTraversal'
                cluster2HostTraversal.selectSet = [host2VmTraversal]

                cluster2DsTraversal = vmodl.query.PropertyCollector.TraversalSpec()
                cluster2DsTraversal.type = vim.ClusterComputeResource
                cluster2DsTraversal.path = 'datastore'
                cluster2DsTraversal.skip = False
                cluster2DsTraversal.name = 'cluster2DsTraversal'

                obj_spec.selectSet = [cluster2HostTraversal,cluster2DsTraversal]
                obj_specs.append(obj_spec)

            return obj_specs

        def createPropertySpecs(mor_types):
            #Create a list of property specifications based on attributes we want to retrieve per entity type
            property_specs = []
            for mor_type in mor_types:
                property_spec = vmodl.query.PropertyCollector.PropertySpec()
                property_spec.type = mor_type
                property_spec.pathSet = ["name", "parent", "customValue"]
                if mor_type == vim.VirtualMachine:
                    property_spec.pathSet.append("runtime.powerState")
                    property_spec.pathSet.append("runtime.host")
                    property_spec.pathSet.append("config.instanceUuid")
                elif mor_type == vim.HostSystem:
                    property_spec.pathSet.append("summary.hardware.uuid")
                elif mor_type == vim.Datastore:
                    property_spec.pathSet.append("info")
                    property_spec.pathSet.append("summary.type")
                property_specs.append(property_spec)

            return property_specs

        def collectProperties(server_instance,error_config,filter_spec,retr_opts):
            mor_properties = {}
            # Collect the objects and their properties
            try:
                collector = server_instance.content.propertyCollector
                res = collector.RetrievePropertiesEx([filter_spec], retr_opts)
                objects = res.objects
                # Results can be paginated
                while res.token is not None:
                    res = collector.ContinueRetrievePropertiesEx(res.token)
                    objects.extend(res.objects)

            except vmodl.query.InvalidProperty, e:
                err_msg = u"InvalidProperty fault while collecting properties : %s , %s" % (e.name, str(e.faultMessage))
                error_config.update({ERR_CODE : 'InvalidProperty'})
                error_config.update({ERR_MSG : err_msg})
                self.log.warning(err_msg)

            except vmodl.fault.InvalidArgument:
                err_msg = u"InvalidArgument fault while collecting properties : %s , %s" % (str(e.invalidProperty), str(e.faultMessage))
                error_config.update({ERR_CODE : 'InvalidArgument'})
                error_config.update({ERR_MSG : err_msg})
                self.log.warning(err_msg)

            except vmodl.fault.InvalidType:
                err_msg = u"InvalidType fault while collecting properties : %s , %s" % (str(e.argument),str(e.faultMessage))
                error_config.update({ERR_CODE : 'InvalidType'})
                error_config.update({ERR_MSG : err_msg})
                self.log.warning(err_msg)

            except vmodl.RuntimeFault, e:
                err_msg = u"Runtime fault while collecting properties : %s , %s" % (str(e.faultCause),str(e.faultMessage))
                error_config.update({ERR_CODE : 'RuntimeFault'})
                error_config.update({ERR_MSG : err_msg})
                self.log.warning(err_msg)

            else:
                for obj in objects:
                    if obj.missingSet:
                        for prop in obj.missingSet:
                            self.log.warning(u"Unable to retrieve property %s for object %s: %s",
                                                            prop.path,str(obj.obj),str(prop.fault))

                    mor_properties[obj.obj] = {prop.name: prop.val for prop in obj.propSet} if obj.propSet else {}

            return mor_properties

        def _collect_metric_mors_and_attributes(server_instance,error_config,clusters):
            obj_specs = createObjectSpecs(clusters)
            property_specs = createPropertySpecs(ALL_RESOURCES_WITH_METRICS)
            #Add the list of object and property specifications to the property filter specification
            filter_spec = vmodl.query.PropertyCollector.FilterSpec()
            filter_spec.objectSet = obj_specs
            filter_spec.propSet = property_specs
            filter_spec.reportMissingObjectsInResults = True

            retr_opts = self.createPropertyOptions()
            mor_attrs = collectProperties(server_instance,error_config,filter_spec,retr_opts)
            return mor_attrs

        def _collect_non_metric_mors_and_attributes(server_instance,error_config):
            #collect the non metric types for parents info
            content = server_instance.content
            view_ref = content.viewManager.CreateContainerView(content.rootFolder, ALL_RESOURCES_WITH_NO_METRICS, True)

            # Specify the root object from where we collect the rest of the objects
            obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
            obj_spec.obj = view_ref
            obj_spec.skip = True

            # Specify the attribute of the root object to traverse to obtain all the attributes
            traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
            traversal_spec.path = "view"
            traversal_spec.skip = False
            traversal_spec.type = view_ref.__class__
            obj_spec.selectSet = [traversal_spec]

            # Specify which attributes we want to retrieve per object
            property_specs = createPropertySpecs(ALL_RESOURCES_WITH_NO_METRICS)

            # Create our filter spec from the above specs
            filter_spec = vmodl.query.PropertyCollector.FilterSpec()
            filter_spec.objectSet = [obj_spec]
            filter_spec.propSet = property_specs
            filter_spec.reportMissingObjectsInResults = True

            retr_opts = self.createPropertyOptions()
            mor_attrs = collectProperties(server_instance,error_config,filter_spec,retr_opts)
            return mor_attrs

        def getDatastoreUuid(mor,properties,datastore_cache):
            ds_uuid = None
            mor_name = str(mor)
            ds_type = properties.get("summary.type")
            ds_info = properties.get("info")
            if mor_name and ds_type and ds_info is not None:
                if ds_type == "VMFS":
                    if ds_info.vmfs is not None:
                        ds_uuid = ds_info.vmfs.uuid
                elif ds_type == "NFS":
                    ds_uuid = datastore_cache.get(mor_name,None)
                    if ds_uuid is None:
                        ds_id = mor_name + ":" + ds_info.url
                        try:
                            ds_id_bytes = ds_id.encode('utf-8')
                            ds_uuid = str(uuid.uuid5(uuid.NAMESPACE_OID, ds_id_bytes))
                            datastore_cache.update({mor_name : ds_uuid})
                        except UnicodeError:
                            self.log.warning(u"Unable to generate uuid for datastore %s",mor_name)
                            ds_uuid = ""
                            pass
                    else:
                        self.log.debug(u"uuid found for datastore %s",mor_name)
                else:
                    self.log.debug(u"Unsupported filesystem volume type : %s",ds_type)

            return ds_uuid

        def getClusterUuid(properties,cluster_cache):
            cluster_uuid = None
            cluster_name = properties.get("name")
            if cluster_name and cluster_cache:
                cluster_uuid = cluster_cache.get(cluster_name,None)
                if cluster_uuid:
                    self.log.debug(u"uuid found for cluster %s",cluster_name)

            return cluster_uuid

        def _get_all_objs(instance, regexes=None, include_only_marked=False, tags=[], clusters = [], uuid_cache = {}):
            """
            Get all the vsphere objects of all types
            """
            server_instance = self._get_server_instance(instance)
            i_key = self._instance_key(instance)
            error_config = self.error_configs[i_key]

            obj_list = defaultdict(list)
            all_mors = {}
            # Collect metric mors and their required attributes
            self.log.debug(u"No. of clusters %d",len(clusters))
            metric_mors = _collect_metric_mors_and_attributes(server_instance,error_config,clusters)
            self.log.debug(u"count of metric mors %d",len(metric_mors))

            if not metric_mors:
                #extract the error config to check why collection failed
                #raise alarms for vcenter errors if any
                error_msg = error_config.get(ERR_MSG)
                error_code = error_config.get(ERR_CODE)
                if error_code and error_msg:
                    self.raiseAlert(instance, error_code, error_msg)
                self.log.error(u"Discovery of metric mors failed : %s",error_msg)
            else:
                all_mors.update(metric_mors)
                # Collect non metric mors and their required attributes
                non_metric_mors = _collect_non_metric_mors_and_attributes(server_instance,error_config)
                self.log.debug(u"count of non metric mors %d",len(non_metric_mors))

                if non_metric_mors:
                    all_mors.update(non_metric_mors)
                else:
                    #extract the error config to check why monitor exited
                    #raise alarms for vcenter errors if any
                    error_msg = error_config.get(ERR_MSG)
                    error_code = error_config.get(ERR_CODE)
                    if error_code and error_msg:
                        self.raiseAlert(instance, error_code, error_msg)
                    self.log.error(u"Discovery of non-metric mors failed: %s",error_msg)

                # Add rootFolder since it is not explored by the propertyCollector
                root_mor = server_instance.content.rootFolder
                all_mors[root_mor] = {"name": root_mor.name, "parent": None}
                self.log.debug(u"Total count of mors %d",len(all_mors))

                for mor, properties in all_mors.items():
                    instance_tags = []
                    mor_type = type(mor)
                    if  mor_type in ALL_RESOURCES_WITH_METRICS and not self._is_excluded(mor, properties, regexes, include_only_marked):
                        hostname = properties.get("name", "unknown")
                        if properties.get("parent"):
                            instance_tags.extend(_get_parent_tags(mor, all_mors))

                        vsphere_type = None
                        entity_type = None
                        entity_id = None

                        if isinstance(mor, vim.VirtualMachine):
                            power_state = properties.get("runtime.powerState")
                            if power_state == vim.VirtualMachinePowerState.poweredOn:
                                host_mor = properties.get("runtime.host")
                                host_props = all_mors.get(host_mor, {})
                                host = "unknown"
                                if host_mor and host_props:
                                    host = host_props.get("name", "unknown")
                                    if self._is_excluded(host_mor, host_props, regexes, include_only_marked):
                                        self.log.debug(u"Skipping VM because host %s is excluded by rule %s.", host, regexes.get('host_include'))
                                        continue
                                instance_tags.append('vsphere_host:{}'.format(host))
                                vsphere_type = u'vsphere_type:vm'
                                entity_id = properties.get("config.instanceUuid","")
                                entity_type = "vm"

                        elif isinstance(mor, vim.HostSystem):
                            vsphere_type = u'vsphere_type:host'
                            entity_type = "node"
                            entity_id = properties.get("summary.hardware.uuid","")

                        elif isinstance(mor, vim.Datastore):
                            vsphere_type = u'vsphere_type:datastore'
                            instance_tags.append(u'vsphere_datastore:{}'.format(properties.get("name", "unknown")))
                            hostname = None
                            entity_type = "container"
                            datastore_cache = uuid_cache.get(vim.Datastore,{})
                            entity_id = getDatastoreUuid(mor,properties,datastore_cache)

                        elif isinstance(mor, vim.ClusterComputeResource):
                            vsphere_type = u'vsphere_type:cluster'
                            instance_tags.append(u'vsphere_cluster:{}'.format(properties.get("name", "unknown")))
                            hostname = None
                            entity_type = "cluster"
                            cluster_cache = uuid_cache.get(vim.ClusterComputeResource,{})
                            entity_id = getClusterUuid(properties,cluster_cache)

                        if entity_type and entity_id:
                            if vsphere_type:
                                instance_tags.append(vsphere_type)
                            obj_dict = dict(mor=mor, hostname=hostname, entity_type=entity_type, entity_id=entity_id, tags=tags+instance_tags)
                            obj_list[mor_type].append(obj_dict)

            return obj_list

        def build_resource_registry(instance, tags, regexes=None, include_only_marked=False):
            i_key = self._instance_key(instance)
            error_config = self.error_configs[i_key]
            if i_key not in self.morlist_raw:
                self.morlist_raw[i_key] = {}

            clusters = self.getClustersToMonitor(instance)
            if clusters:
                uuid_cache = self.cache_uuids[i_key]
                all_objs = _get_all_objs(instance,regexes,include_only_marked,tags,clusters,uuid_cache)
                self.morlist_raw[i_key] = all_objs
            else:
                #extract the error config to check why monitor exited
                #raise alarms for vcenter errors if any
                error_msg = error_config.get(ERR_MSG)
                error_code = error_config.get(ERR_CODE)
                if error_code and error_msg:
                    self.raiseAlert(instance, error_code, error_msg)

        # enumerate and build inventory of resources...
        build_resource_registry(instance, tags, regexes, include_only_marked)

    @staticmethod
    def _is_excluded(obj, properties, regexes, include_only_marked):
        """
        Return `True` if the given host or virtual machine is excluded by the user configuration,
        i.e. violates any of the following rules:
        * Do not match the corresponding `*_include_only` regular expressions
        * Is "non-labeled" while `include_only_marked` is enabled (virtual machine only)
        """
        # Host
        if isinstance(obj, vim.HostSystem):
            # Based on `host_include_only_regex`
            if regexes and regexes.get('host_include') is not None:
                match = re.search(regexes['host_include'], obj.name)
                if not match:
                    return True

        # VirtualMachine
        elif isinstance(obj, vim.VirtualMachine):
            # Based on `vm_include_only_regex`
            if regexes and regexes.get('vm_include') is not None:
                match = re.search(regexes['vm_include'], obj.name)
                if not match:
                    return True

            # Based on `include_only_marked`
            if include_only_marked:
                monitored = False
                for field in properties.get('customValue',''):
                    if field.value == VM_MONITORING_FLAG:
                        monitored = True
                        break  # we shall monitor
                if not monitored:
                    return True

        return False

    def _cache_morlist_raw(self, instance):
        """
        Initiate the first layer to refresh the list of MORs (`self.morlist`).

        Resolve the vCenter `rootFolder` and initiate hosts and virtual machines discovery.

        """

        i_key = self._instance_key(instance)
        self.log.info(u"Caching the morlist for vcenter instance %s" % i_key)
        for resource_type in ALL_RESOURCES_WITH_METRICS:
            if i_key in self.morlist_raw and len(self.morlist_raw[i_key].get(resource_type, [])) > 0:
                self.log.info(
                    "Skipping morlist collection now, RAW results "
                    "processing not over (latest refresh was {0}s ago)".format(
                        time.time() - self.cache_times[i_key][MORLIST][LAST])
                )
                return
        self.morlist_raw[i_key] = {}

        instance_tag = "vcenter_server:%s" % instance.get('name')
        regexes = {
            'host_include': instance.get('host_include_only_regex'),
            'vm_include': instance.get('vm_include_only_regex')
        }
        include_only_marked = _is_affirmative(instance.get('include_only_marked', False))

        # Discover hosts and virtual machines
        self._discover_mor(instance, [instance_tag], regexes, include_only_marked)

        self.cache_times[i_key][MORLIST][LAST] = time.time()

    def _cache_morlist_process(self, instance):
        """ Empties the self.morlist_raw by popping items and running asynchronously
        the _cache_morlist_process_atomic operation that will get the available
        metrics for this MOR and put it in self.morlist
        """
        i_key = self._instance_key(instance)
        if i_key not in self.morlist:
            self.morlist[i_key] = {}

        # Simply move the mors from the morlist_raw to the morlist
        for resource_type in ALL_RESOURCES_WITH_METRICS:
            mors = self.morlist_raw[i_key].pop(resource_type,[])
            if resource_type not in self.morlist[i_key]:
                self.morlist[i_key][resource_type] = {}
            for mor in mors:
                mor_name = str(mor['mor'])
                self.morlist[i_key][resource_type][mor_name] = mor
                #update timestamp
                self.morlist[i_key][resource_type][mor_name]['last_seen'] = time.time()

    def _vacuum_morlist(self, instance):
        """ Check if self.morlist doesn't have some old MORs that are gone, ie
        we cannot get any metrics from them anyway (or =0)
        """
        i_key = self._instance_key(instance)
        for resource_type in ALL_RESOURCES_WITH_METRICS:
            morlist = self.morlist[i_key].get(resource_type,{}).items()
            for mor_name, mor in morlist:
                last_seen = mor['last_seen']
                if (time.time() - last_seen) > 2 * REFRESH_MORLIST_INTERVAL:
                    del self.morlist[i_key][resource_type][mor_name]
                    if resource_type in HISTORICAL_RESOURCES and mor_name in self.cache_uuids[i_key][resource_type]:
                        del self.cache_uuids[i_key][resource_type][mor_name]
                    self.log.debug(u"deleted mor %s",mor_name)

    def format_metric_name(self,counter):
        return "{}.{}.{}".format(counter.groupInfo.key,counter.nameInfo.key,str(counter.rollupType))

    def _cache_metrics_metadata(self, instance):
        """ Get from the server instance, all the performance counters metadata
        meaning name/group/description... attached with the corresponding ID
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>

        i_key = self._instance_key(instance)
        self.log.info(u"Warming metrics metadata cache for instance {0}".format(i_key))
        server_instance = self._get_server_instance(instance)
        perfManager = server_instance.content.perfManager
        custom_tags = instance.get('tags', [])

        counters = perfManager.perfCounter
        new_metadata = {}
        for mor_type in ALL_RESOURCES_WITH_METRICS:
            new_metadata[mor_type] = {}
            for counter in counters:
                metric_name = self.format_metric_name(counter)
                if metric_name in ALLOWED_METRICS_FOR_MOR[mor_type]:
                    new_metadata[mor_type][counter.key] = dict(name = metric_name, unit=counter.unitInfo.key)

        self.log.debug(u"Collected %d counters metadata in %.3f seconds.", len(counters), t.total())
        self.log.info(u"Finished metadata collection for instance {0}".format(i_key))
        # Reset metadata
        self.metrics_metadata[i_key] = new_metadata

        #update the timestamp
        self.cache_times[i_key][METRICS_METADATA][LAST] = time.time()

        # ## <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.metric_metadata_collection.time', t.total(), tags=custom_tags)
        # ## </TEST-INSTRUMENTATION>

    def _transform_value(self, instance, counter_id, mor_type, value):
        """ Given the counter_id, look up for the metrics metadata to check the vsphere
        type of the counter and apply pre-reporting transformation if needed.
        """
        i_key = self._instance_key(instance)
        if counter_id in self.metrics_metadata[i_key][mor_type]:
            unit = self.metrics_metadata[i_key][mor_type][counter_id]['unit']
            if unit == 'percent':
                return float(value) / 100

        # Defaults to return the value without transformation
        return value

    @atomic_method
    def _collect_metrics_atomic(self, instance, query_specs):
        """ Task that collects the metrics listed in the batch of query specs
        """
        # ## <TEST-INSTRUMENTATION>
        t = Timer()
        # ## </TEST-INSTRUMENTATION>

        i_key = self._instance_key(instance)
        server_instance = self._get_server_instance(instance)
        error_config = {ERR_CODE : None,ERR_MSG : None}
        perfManager = server_instance.content.perfManager
        custom_tags = instance.get('tags', [])
        try:
            results = perfManager.QueryPerf(querySpec=query_specs)
            if results:
                for entity_metrics in results:
                    mor_name = str(entity_metrics.entity)
                    mor_type = type(entity_metrics.entity)
                    try:
                        mor = self.morlist[i_key][mor_type][mor_name]
                    except KeyError:
                        self.log.error(u"Trying to get metrics from object %s deleted from the cache, skipping.",mor_name)
                        continue

                    for perf_metric in entity_metrics.value:
                        counter_id = perf_metric.id.counterId
                        if counter_id not in self.metrics_metadata[i_key][mor_type]:
                            self.log.debug(u"Skipping this metric value %d, because there is no metadata about it",counter_id)
                            continue

                        # Metric types are absolute, delta, and rate
                        try:
                            metric_name = self.metrics_metadata[i_key][mor_type][counter_id]['name']
                        except KeyError:
                            self.log.debug(u"Skipping this metric value %d, because of missing metric name",counter_id)
                            continue

                        if not perf_metric.value:
                            self.log.debug(u"Skipping `%s` metric because the value is empty", metric_name)
                            continue

                        instance_name = perf_metric.id.instance or "none"
                        # Get the most recent value that isn't negative
                        valid_values = [v for v in perf_metric.value if v >= 0]
                        if not valid_values:
                            continue

                        value = self._transform_value(instance, counter_id, mor_type, valid_values[-1])

                        tags = ['instance:%s' % instance_name]
                        if not mor['hostname']:  # no host tags available
                            tags.extend(mor['tags'])

                        if custom_tags:
                            tags.extend(custom_tags)

                        #add the entity id and type to tags
                        entity_tags = []
                        entity_id = mor.get('entity_id',None)
                        entity_type = mor.get('entity_type',None)
                        if entity_id:
                            entity_tags.append('entity_id:%s' %entity_id)
                        if entity_type:
                            entity_tags.append('entity_type:%s' %entity_type)

                        if entity_tags:
                            tags.extend(entity_tags)

                        self.log.debug(u"query results for %s : %f tags : %s",metric_name,value,tags)

                        # vsphere "rates" should be submitted as gauges (rate is
                        # precomputed).
                        self.gauge(
                            "vsphere.%s" % metric_name,
                            value,
                            hostname=mor['hostname'],
                            tags=tags
                        )
        except vmodl.fault.InvalidArgument , e:
            err_msg = u"InvalidArgument fault while querying perf metrics : %s , %s" % (str(e.invalidProperty), str(e.faultMessage))
            error_config.update({ERR_CODE : 'InvalidArgument'})
            error_config.update({ERR_MSG : err_msg})
            self.log.warning(err_msg)
        except vim.fault.RestrictedByAdministrator , e:
            err_msg = u"RestrictedByAdministrator fault while querying perf metrics : %s , %s" % (str(e.details), str(e.faultMessage))
            error_config.update({ERR_CODE : 'RestrictedByAdministrator'})
            error_config.update({ERR_MSG : err_msg})
            self.log.warning(err_msg)
        except vmodl.RuntimeFault , e:
            err_msg = u"Runtime fault while querying perf metrics : %s , %s" % (str(e.faultCause),str(e.faultMessage))
            error_config.update({ERR_CODE : 'RuntimeFault'})
            error_config.update({ERR_MSG : err_msg})
            self.log.warning(err_msg)

        #extract the error config to check why monitor exited
        #raise alarms for vcenter errors if any
        error_msg = error_config.get(ERR_MSG)
        error_code = error_config.get(ERR_CODE)
        if error_msg and error_code:
            self.raiseAlert(instance, error_code, error_msg)

        # ## <TEST-INSTRUMENTATION>
        self.histogram('datadog.agent.vsphere.metric_colection.time', t.total(), tags=custom_tags)
        # ## </TEST-INSTRUMENTATION>

    def get_batch_size(self,resource_type):
        # return the max batch size based on resource type
        if resource_type == vim.ClusterComputeResource:
            # Collect cluster metrics one by one.
            max_batch_size = 1
        elif resource_type in REALTIME_RESOURCES or self.max_historical_metrics < 0:
            # Queries are not limited by vCenter
            max_batch_size = self.metrics_per_query
        else:
            # Collection is limited by the value of `max_query_metrics`
            if self.metrics_per_query < 0:
                max_batch_size = self.max_historical_metrics
            else:
                max_batch_size = min(self.metrics_per_query, self.max_historical_metrics)

        return max_batch_size

    def make_batch(self, mors, metric_ids, max_batch_size):
        """Iterates over mors and generate batches with a fixed number of metrics to query.
        """
        batch = defaultdict(list)
        batch_size = 0
        for mor in mors:
            mor_obj = mor['mor']
            for metric in metric_ids:
                if batch_size == max_batch_size:
                    yield batch
                    batch = defaultdict(list)
                    batch_size = 0
                batch[mor_obj].append(metric)
                batch_size += 1
        # Do not yield an empty batch
        if batch:
            yield batch

    def make_query_specs(self,instance):
        """
        Build query specs using MORs and metrics metadata.
        :returns a list of vim.PerformanceManager.QuerySpec:
        https://www.vmware.com/support/developer/vc-sdk/visdk41pubs/ApiReference/vim.PerformanceManager.QuerySpec.html
        """
        i_key = self._instance_key(instance)
        if i_key not in self.morlist:
            self.log.info(u"Not collecting metrics for this instance, nothing to do yet: {0}".format(i_key))
            return

        for resource_type in ALL_RESOURCES_WITH_METRICS:
            # Safeguard, let's avoid collecting multiple resource types in the same call
            # get entire list of mors with matching resource_type
            mors = self.morlist[i_key].get(resource_type,{}).values()
            self.log.debug(u"make query specs for %d mors of type %s",len(mors),resource_type)
            max_batch_size = self.get_batch_size(resource_type)
            counters = self.metrics_metadata[i_key].get(resource_type,{})
            # - An asterisk (*) to specify all instances of the metric for the specified counterId
            # - Double-quotes ("") to specify aggregated statistics
            if resource_type in REALTIME_RESOURCES:
                instance_value = "*"
            else:
                instance_value = ""
            metric_ids = []
            for counter_key in counters.keys():
                metric_ids.append(vim.PerformanceManager.MetricId(counterId=counter_key, instance=instance_value))

            for batch in self.make_batch(mors, metric_ids, max_batch_size):
                query_specs = []
                for mor, metrics in batch.items():
                    query_spec = vim.PerformanceManager.QuerySpec()
                    query_spec.entity = mor
                    query_spec.metricId = metrics
                    query_spec.format = "normal"
                    if resource_type in REALTIME_RESOURCES:
                        query_spec.intervalId = REAL_TIME_INTERVAL
                        query_spec.maxSample = 1  # Request a single datapoint
                    else:
                        # We cannot use `maxSample` for historical metrics, let's specify a timewindow that will
                        # contain at least one element
                        query_spec.startTime = datetime.now() - timedelta(hours=2)

                    query_specs.append(query_spec)
                if query_specs:
                    yield query_specs

    def collect_metrics(self, instance):
        """ Calls asynchronously _collect_metrics_atomic on all MORs, as the
        job queue is processed the Aggregator will receive the metrics.
        """
        i_key = self._instance_key(instance)
        if i_key not in self.morlist:
            self.log.debug(u"Not collecting metrics for this instance, nothing to do yet: {0}".format(i_key))
            return

        custom_tags = instance.get('tags', [])
        n_mors = 0
        vm_count = 0
        for resource_type in ALL_RESOURCES_WITH_METRICS:
            mors = self.morlist[i_key].get(resource_type,{})
            mor_count = len(mors)
            if resource_type == vim.HostSystem:
                self.log.debug(u"Host count %d",mor_count)
            if resource_type == vim.ClusterComputeResource:
                self.log.debug(u"Cluster count %d",mor_count)
            if resource_type == vim.Datastore:
                self.log.debug(u"Datastore count %d",mor_count)
            if resource_type == vim.VirtualMachine:
                self.log.debug(u"Vm count %d",mor_count)
                vm_count = mor_count

            n_mors += mor_count

        self.log.debug(u"Collecting metrics of %d mors",n_mors)

        for query_specs in self.make_query_specs(instance):
            if query_specs:
                self.pool.apply_async(self._collect_metrics_atomic, args=(instance, query_specs))

        self.gauge('vsphere.vm.count', vm_count, tags=["vcenter_server:%s" % instance.get('name')] + custom_tags)

    def check(self, instance):
        if not self.pool_started:
            self.start_pool()

        custom_tags = instance.get('tags', [])

        # Update the value of `max_query_metrics` if needed
        server_instance = self._get_server_instance(instance)
        try:
            vcenter_settings = server_instance.content.setting.QueryOptions(MAX_QUERY_METRICS_OPTION)
            vcenter_max_hist_metrics = int(vcenter_settings[0].value)
            if vcenter_max_hist_metrics < 0:
                self.max_historical_metrics = float('inf')
            else:
                self.max_historical_metrics = vcenter_max_hist_metrics
        except Exception:
            self.max_historical_metrics = DEFAULT_MAX_QUERY_METRICS
            self.log.debug(u"Could not fetch the value of %s, setting `max_historical_metrics` to default value %d.",
                                                                MAX_QUERY_METRICS_OPTION,DEFAULT_MAX_QUERY_METRICS)
            pass

        # ## <TEST-INSTRUMENTATION>
        self.gauge('datadog.agent.vsphere.queue_size', self.pool._workq.qsize(), tags=['instant:initial'] + custom_tags)
        # ## </TEST-INSTRUMENTATION>

        # First part: make sure our object repository is neat & clean
        if self._should_cache(instance, METRICS_METADATA):
            self._cache_metrics_metadata(instance)

        if self._should_cache(instance, MORLIST):
            self._cache_morlist_raw(instance)

        self._cache_morlist_process(instance)
        self._vacuum_morlist(instance)

        # Second part: do the job
        self.collect_metrics(instance)
        self._query_event(instance)

        # For our own sanity
        self._clean()

        thread_crashed = False
        try:
            while True:
                self.log.critical(self.exceptionq.get_nowait())
                thread_crashed = True
        except Empty:
            pass

        if thread_crashed:
            self.stop_pool()
            raise Exception("One thread in the pool crashed, check the logs")

        if set_external_tags is not None:
            set_external_tags(self.get_external_host_tags())

        # ## <TEST-INSTRUMENTATION>
        self.gauge('datadog.agent.vsphere.queue_size', self.pool._workq.qsize(), tags=['instant:final'] + custom_tags)
        # ## </TEST-INSTRUMENTATION>
