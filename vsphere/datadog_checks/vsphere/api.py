# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import functools
import ssl

from pyVim import connect
from pyVmomi import vim, vmodl

from datadog_checks.vsphere.constants import ALL_RESOURCES, MAX_QUERY_METRICS_OPTION, UNLIMITED_HIST_METRICS_PER_QUERY

# Python 3 only
PROTOCOL_TLS_CLIENT = getattr(ssl, 'PROTOCOL_TLS_CLIENT', ssl.PROTOCOL_TLS)


def smart_retry(f):
    """A function decorated with this `@smart_retry` will trigger a new authentication if it fails. The function
    will then be retried.
    This is useful when the integration keeps a semi-healthy connection to the vSphere API"""

    @functools.wraps(f)
    def wrapper(api_instance, *args, **kwargs):
        try:
            return f(api_instance, *args, **kwargs)
        except Exception as e:
            api_instance.log.debug(
                "An exception occurred when executing %s: %s. Refreshing the connection to vCenter and retrying",
                f.__name__,
                e,
            )
            api_instance.smart_connect()
            return f(api_instance, *args, **kwargs)

    return wrapper


class APIConnectionError(Exception):
    pass


class APIResponseError(Exception):
    pass


class VSphereAPI(object):
    """Abstraction class over the vSphere SOAP api using the pyvmomi library"""

    def __init__(self, config, log):
        self.config = config
        self.log = log

        self._conn = None
        self.smart_connect()

    def smart_connect(self):
        """Creates the connection object to the vSphere API using parameters supplied from the configuration.
        """
        context = None
        if not self.config.ssl_verify:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            context.verify_mode = ssl.CERT_NONE
        elif self.config.ssl_capath:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            context.verify_mode = ssl.CERT_REQUIRED
            context.load_verify_locations(capath=self.config.ssl_capath)

        try:
            # Object returned by SmartConnect is a ServerInstance
            # https://www.vmware.com/support/developer/vc-sdk/visdk2xpubs/ReferenceGuide/vim.ServiceInstance.html
            conn = connect.SmartConnect(
                host=self.config.hostname, user=self.config.username, pwd=self.config.password, sslContext=context
            )
            # Next line tries a simple API call to check the health of the connection.
            conn.CurrentTime()
        except Exception as e:
            err_msg = "Connection to {} failed: {}".format(self.config.hostname, e)
            raise APIConnectionError(err_msg)

        self._conn = conn

    @smart_retry
    def check_health(self):
        self._conn.CurrentTime()

    @smart_retry
    def get_perf_counter_by_level(self, collection_level):
        """
        Requests and returns the list of counter available for a given collection_level.

        :return list of vim.PerformanceManager.CounterInfo:
        https://vdc-download.vmware.com/vmwb-repository/dcr-public/fe08899f-1eec-4d8d-b3bc-a6664c168c2c/7fdf97a1-4c0d-4be0-9d43-2ceebbc174d9/doc/vim.PerformanceManager.CounterInfo.html
        """
        return self._conn.content.perfManager.QueryPerfCounterByLevel(collection_level)

    @smart_retry
    def get_infrastructure(self):
        """Traverse the whole vSphere infrastructure and outputs a dict mapping the mors to their properties.

        :return: {
            'vim.VirtualMachine-VM0': {
              'name': 'VM-0',
              ...
            }
            ...
        }
        """
        content = self._conn.content  # vim.ServiceInstanceContent reference from the connection

        property_specs = []
        # Specify which attributes we want to retrieve per object
        for resource in ALL_RESOURCES:
            property_spec = vmodl.query.PropertyCollector.PropertySpec()
            property_spec.type = resource
            property_spec.pathSet = ["name", "parent", "customValue"]
            if resource == vim.VirtualMachine:
                property_spec.pathSet.append("runtime.powerState")
                property_spec.pathSet.append("runtime.host")
                property_spec.pathSet.append("guest.hostName")
            property_specs.append(property_spec)

        # Specify the attribute of the root object to traverse to obtain all the attributes
        traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.path = "view"
        traversal_spec.skip = False
        traversal_spec.type = vim.view.ContainerView

        retr_opts = vmodl.query.PropertyCollector.RetrieveOptions()
        # To limit the number of objects retrieved per call.
        # If batch_collector_size is 0, collect maximum number of objects.
        retr_opts.maxObjects = self.config.batch_collector_size

        # Specify the root object from where we collect the rest of the objects
        obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.skip = True
        obj_spec.selectSet = [traversal_spec]

        # Create our filter spec from the above specs
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.propSet = property_specs

        view_ref = content.viewManager.CreateContainerView(content.rootFolder, ALL_RESOURCES, True)
        try:
            obj_spec.obj = view_ref
            filter_spec.objectSet = [obj_spec]

            # Collect the objects and their properties
            res = content.propertyCollector.RetrievePropertiesEx([filter_spec], retr_opts)
            mors = res.objects
            # Results can be paginated
            while res.token is not None:
                res = content.propertyCollector.ContinueRetrievePropertiesEx(res.token)
                mors.extend(res.objects)
        finally:
            view_ref.Destroy()

        infrastructure_data = {mor.obj: {prop.name: prop.val for prop in mor.propSet} for mor in mors if mor.propSet}

        root_folder = self._conn.content.rootFolder
        infrastructure_data[root_folder] = {"name": root_folder.name, "parent": None}
        return infrastructure_data

    @smart_retry
    def query_metrics(self, query_specs):
        perf_manager = self._conn.content.perfManager
        values = perf_manager.QueryPerf(query_specs)
        return values

    @smart_retry
    def get_new_events(self, start_time):
        event_manager = self._conn.content.eventManager
        query_filter = vim.event.EventFilterSpec()
        time_filter = vim.event.EventFilterSpec.ByTime(beginTime=start_time)
        query_filter.time = time_filter
        return event_manager.QueryEvents(query_filter)

    @smart_retry
    def get_latest_event_timestamp(self):
        event_manager = self._conn.content.eventManager
        return event_manager.latestEvent.createdTime

    @smart_retry
    def get_max_query_metrics(self):
        vcenter_settings = self._conn.content.setting.QueryOptions(MAX_QUERY_METRICS_OPTION)
        max_historical_metrics = int(vcenter_settings[0].value)
        return max_historical_metrics if max_historical_metrics > 0 else UNLIMITED_HIST_METRICS_PER_QUERY
