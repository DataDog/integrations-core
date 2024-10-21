# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

import datetime as dt
import logging
from collections import defaultdict
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any, Callable, Dict, Generator, Iterable, List, Optional, Set, Type, cast  # noqa: F401

from pyVmomi import vim, vmodl

from datadog_checks.base import AgentCheck, is_affirmative, to_string
from datadog_checks.base.checks.libs.timer import Timer
from datadog_checks.base.utils.time import get_current_datetime, get_timestamp
from datadog_checks.vsphere.api import APIConnectionError, VSphereAPI
from datadog_checks.vsphere.api_rest import VSphereRestAPI
from datadog_checks.vsphere.cache import InfrastructureCache, MetricsMetadataCache
from datadog_checks.vsphere.config import VSphereConfig
from datadog_checks.vsphere.constants import (
    DEFAULT_MAX_QUERY_METRICS,
    HISTORICAL,
    HOST_RESOURCES,
    MAX_QUERY_METRICS_OPTION,
    PROPERTY_COUNT_METRICS,
    PROPERTY_METRICS_BY_RESOURCE_TYPE,
    REALTIME_METRICS_INTERVAL_ID,
    UNLIMITED_HIST_METRICS_PER_QUERY,
)
from datadog_checks.vsphere.event import VSphereEvent
from datadog_checks.vsphere.metrics import ALLOWED_METRICS_FOR_MOR, PERCENT_METRICS
from datadog_checks.vsphere.resource_filters import TagFilter
from datadog_checks.vsphere.types import (
    CounterId,  # noqa: F401
    InfrastructureData,  # noqa: F401
    InfrastructureDataItem,  # noqa: F401
    InstanceConfig,
    MetricName,  # noqa: F401
    MorBatch,  # noqa: F401
    ResourceTags,  # noqa: F401
    VmomiObject,  # noqa: F401
)
from datadog_checks.vsphere.utils import (
    MOR_TYPE_AS_STRING,
    add_additional_tags,
    format_metric_name,
    get_mapped_instance_tag,
    get_tags_recursively,
    is_metric_allowed_for_collection_type,
    is_metric_excluded_by_filters,
    is_resource_collected_by_filters,
    should_collect_per_instance_values,
)

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent


SERVICE_CHECK_NAME = 'can_connect'


class VSphereCheck(AgentCheck):
    __NAMESPACE__ = 'vsphere'

    def __new__(cls, name, init_config, instances):
        # type: (Type[VSphereCheck], str, Dict[str, Any], List[Dict[str, Any]]) -> VSphereCheck
        """For backward compatibility reasons, there are two side-by-side implementations of the VSphereCheck.
        Instantiating this class will return an instance of the legacy integration for existing users and
        an instance of the new implementation for new users."""
        if is_affirmative(instances[0].get('use_legacy_check_version', True)):
            from datadog_checks.vsphere.legacy.vsphere_legacy import VSphereLegacyCheck

            return VSphereLegacyCheck(name, init_config, instances)  # type: ignore
        return super(VSphereCheck, cls).__new__(cls)

    def __init__(self, *args, **kwargs):
        # type: (*Any, **Any) -> None
        super(VSphereCheck, self).__init__(*args, **kwargs)
        instance = cast(InstanceConfig, self.instance)
        self._config = VSphereConfig(instance, self.init_config, self.log)

        self.latest_event_query = get_current_datetime()
        self.infrastructure_cache = InfrastructureCache(interval_sec=self._config.refresh_infrastructure_cache_interval)
        self.metrics_metadata_cache = MetricsMetadataCache(
            interval_sec=self._config.refresh_metrics_metadata_cache_interval
        )
        self.api = cast(VSphereAPI, None)
        self.api_rest = cast(VSphereRestAPI, None)
        # Do not override `AgentCheck.hostname`
        self._hostname = None
        self.thread_pool = ThreadPoolExecutor(max_workers=self._config.threads_count)
        self.check_initializations.append(self.initiate_api_connection)

        self.last_connection_time = get_timestamp()

    def initiate_api_connection(self):
        # type: () -> None
        try:
            self.log.debug(
                "Connecting to the vCenter API %s with username %s...", self._config.hostname, self._config.username
            )
            self.api = VSphereAPI(self._config, self.log)
            self.log.debug("Connected")
        except APIConnectionError:
            # Clear the API connection object if the authentication fails
            self.api = cast(VSphereAPI, None)
            self.log.error("Cannot authenticate to vCenter API. The check will not run.")
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._config.base_tags, hostname=None)
            raise

        if self._config.should_collect_tags:
            try:
                version_info = self.api.get_version()
                major_version = int(version_info.version_str[0])

                if major_version >= 7:
                    try:
                        # Try to connect to REST API vSphere v7
                        self.api_rest = VSphereRestAPI(self._config, self.log, False)
                        return
                    except Exception:
                        self.log.debug("REST API of vSphere 7 not detected, falling back to the old API.")
                self.api_rest = VSphereRestAPI(self._config, self.log, True)
            except Exception as e:
                self.log.error("Cannot connect to vCenter REST API. Tags won't be collected. Error: %s", e)

    def refresh_metrics_metadata_cache(self):
        # type: () -> None
        """
        Request the list of counters (metrics) from vSphere and store them in a cache.
        """
        self.log.debug(
            "Refreshing the metrics metadata cache. Collecting all counters metadata for collection_level=%d",
            self._config.collection_level,
        )
        t0 = Timer()
        counters = self.api.get_perf_counter_by_level(self._config.collection_level)
        self.gauge(
            "datadog.vsphere.refresh_metrics_metadata_cache.time",
            t0.total(),
            tags=self._config.base_tags,
            raw=True,
            hostname=self._hostname,
        )
        self.log.debug("Collected %d counters metadata in %.3f seconds.", len(counters), t0.total())

        for mor_type in self._config.collected_resource_types:
            allowed_counters = []
            for c in counters:
                metric_name = format_metric_name(c)
                if is_metric_allowed_for_collection_type(
                    mor_type, metric_name, self._config.collection_type
                ) and not is_metric_excluded_by_filters(metric_name, mor_type, self._config.metric_filters):
                    allowed_counters.append(c)
            metadata = {c.key: format_metric_name(c) for c in allowed_counters}  # type: Dict[CounterId, MetricName]
            self.metrics_metadata_cache.set_metadata(mor_type, metadata)
            self.log.debug(
                "Set metadata for mor_type %s: %s",
                mor_type,
                metadata,
            )

        # TODO: Later - Understand how much data actually changes between check runs
        # Apparently only when the server restarts?
        # https://pubs.vmware.com/vsphere-50/index.jsp?topic=%2Fcom.vmware.wssdk.pg.doc_50%2FPG_Ch16_Performance.18.5.html

    def collect_tags(self, infrastructure_data):
        # type: (InfrastructureData) -> ResourceTags
        """
        Fetch the all tags, build tags for each monitored resources and store all of that into the tags_cache.
        """
        if not self.api_rest:
            return {}

        # In order to be more efficient in tag collection, the infrastructure data is filtered as much as possible.
        # All filters are applied except the ones based on tags of course.
        resource_filters_without_tags = [f for f in self._config.resource_filters if not isinstance(f, TagFilter)]
        filtered_infra_data = {
            mor: props
            for mor, props in infrastructure_data.items()
            if isinstance(mor, tuple(self._config.collected_resource_types))
            and is_resource_collected_by_filters(mor, infrastructure_data, resource_filters_without_tags)
        }

        t0 = Timer()
        mors_list = list(filtered_infra_data.keys())
        try:
            mor_tags = self.api_rest.get_resource_tags_for_mors(mors_list)
        except Exception as e:
            self.log.error("Failed to collect tags: %s", e)
            return {}

        self.gauge(
            'datadog.vsphere.query_tags.time',
            t0.total(),
            tags=self._config.base_tags,
            raw=True,
            hostname=self._hostname,
        )

        return mor_tags

    def refresh_infrastructure_cache(self):
        # type: () -> None
        """Fetch the complete infrastructure, generate tags for each monitored resources and store all of that
        into the infrastructure_cache. It also computes the resource `hostname` property to be used when submitting
        metrics for this mor."""
        self.log.debug("Refreshing the infrastructure cache...")
        t0 = Timer()
        infrastructure_data = self.api.get_infrastructure()
        collect_property_metrics = self._config.collect_property_metrics
        self.gauge(
            "datadog.vsphere.refresh_infrastructure_cache.time",
            t0.total(),
            tags=self._config.base_tags + ['collect_property_metrics:{}'.format(collect_property_metrics)],
            raw=True,
            hostname=self._hostname,
        )
        self.log.debug("Infrastructure cache refreshed in %.3f seconds.", t0.total())

        # When collecting property metrics, there are pyVmomi objects in the cache at this point
        if collect_property_metrics:
            self.log.trace("Infrastructure cache with properties: %s", infrastructure_data)
        else:
            self.log.debug("Infrastructure cache: %s", infrastructure_data)

        all_tags = {}
        if self._config.should_collect_tags:
            all_tags = self.collect_tags(infrastructure_data)
        self.infrastructure_cache.set_all_tags(all_tags)

        for mor, properties in infrastructure_data.items():
            if not isinstance(mor, tuple(self._config.collected_resource_types)):
                # Do nothing for the resource types we do not collect
                continue

            mor_name = to_string(properties.get("name", "unknown"))
            mor_type_str = MOR_TYPE_AS_STRING[type(mor)]
            hostname = None
            tags = []
            mor_payload = {}  # type: Dict[str, Any]
            if self._config.collect_property_metrics:
                all_properties = properties.get('properties', {})
                mor_payload['properties'] = all_properties

            if isinstance(mor, vim.VirtualMachine):
                power_state = properties.get("runtime.powerState")
                if power_state != vim.VirtualMachinePowerState.poweredOn:
                    # Skipping because the VM is not powered on
                    # TODO: Sometimes VM are "poweredOn" but "disconnected" and thus have no metrics
                    self.log.debug("Skipping VM %s in state %s", mor_name, to_string(power_state))
                    continue

                # Hosts are not considered as parents of the VMs they run, we use the `runtime.host` property
                # to get the name of the ESXi host
                runtime_host = properties.get("runtime.host")
                runtime_host_props = {}  # type: InfrastructureDataItem
                if runtime_host:
                    if runtime_host in infrastructure_data:
                        runtime_host_props = infrastructure_data.get(runtime_host, {})
                    else:
                        self.log.debug("Missing runtime.host details for VM %s", mor_name)
                runtime_hostname = to_string(runtime_host_props.get("name", "unknown"))
                tags.append('vsphere_host:{}'.format(runtime_hostname))

                if self._config.use_guest_hostname:
                    hostname = properties.get("guest.hostName", mor_name)
                else:
                    hostname = mor_name
            elif isinstance(mor, vim.HostSystem):
                hostname = mor_name

            else:
                tags.append('vsphere_{}:{}'.format(mor_type_str, mor_name))

            parent = properties.get('parent')
            runtime_host = properties.get('runtime.host')
            if parent is not None:
                tags.extend(
                    get_tags_recursively(parent, infrastructure_data, self._config.include_datastore_cluster_folder_tag)
                )
            if runtime_host is not None:
                tags.extend(
                    get_tags_recursively(
                        runtime_host,
                        infrastructure_data,
                        self._config.include_datastore_cluster_folder_tag,
                        include_only=['vsphere_cluster'],
                    )
                )
            tags.append('vsphere_type:{}'.format(mor_type_str))

            # Attach tags from fetched attributes.
            tags.extend(properties.get('attributes', []))
            resource_tags = self.infrastructure_cache.get_mor_tags(mor) + tags
            if not is_resource_collected_by_filters(
                mor,
                infrastructure_data,
                self._config.resource_filters,
                resource_tags,
            ):
                # The resource does not match the specified whitelist/blacklist patterns.
                self.log.debug(
                    "Skipping resource not matched by filters. resource=`%s` tags=`%s`", mor_name, resource_tags
                )
                continue

            # after retrieving tags, add hostname suffix if specified
            if isinstance(mor, vim.VirtualMachine):
                if self._config.vm_hostname_suffix_tag is not None:
                    hostname_suffix = None

                    all_tags = resource_tags + self._config.custom_tags
                    sorted_tags = sorted(all_tags)
                    for resource_tag in sorted_tags:
                        resource_tag_key, _, resource_tag_value = resource_tag.partition(":")
                        if resource_tag_key == self._config.vm_hostname_suffix_tag:
                            hostname_suffix = resource_tag_value
                            break

                    if hostname_suffix is not None:
                        hostname = "{}-{}".format(hostname, hostname_suffix)
                        self.log.debug(
                            "Attached hostname suffix key %s, new hostname: %s",
                            self._config.vm_hostname_suffix_tag,
                            hostname,
                        )

                    else:
                        self.log.debug(
                            "Could not attach hostname suffix key %s for host: %s",
                            self._config.vm_hostname_suffix_tag,
                            hostname,
                        )

            mor_payload["tags"] = tags  # type: Dict[str, Any]

            if hostname:
                if self._config.hostname_transform == 'upper':
                    hostname = hostname.upper()
                elif self._config.hostname_transform == 'lower':
                    hostname = hostname.lower()
                mor_payload['hostname'] = hostname

            self.infrastructure_cache.set_mor_props(mor, mor_payload)

    def submit_metrics_callback(self, query_results):
        # type: (List[vim.PerformanceManager.EntityMetricBase]) -> None
        """
        Callback of the collection of metrics. This is run in the main thread!

        `query_results` currently contain results of one resource type in practice, but this function is generic
        and can handle results with mixed resource types.
        """

        # `have_instance_value` is used later to avoid collecting aggregated metrics
        # when instance metrics are collected.
        have_instance_value = defaultdict(set)  # type: Dict[Type[vim.ManagedEntity], Set[MetricName]]
        for results_per_mor in query_results:
            resource_type = type(results_per_mor.entity)
            metadata = self.metrics_metadata_cache.get_metadata(resource_type)
            for result in results_per_mor.value:
                if result.id.instance:
                    counter_id = metadata.get(result.id.counterId)
                    if counter_id:
                        have_instance_value[resource_type].add(counter_id)

        for results_per_mor in query_results:
            mor_props = self.infrastructure_cache.get_mor_props(results_per_mor.entity)
            if mor_props is None:
                self.log.debug(
                    "Skipping results for mor %s because the integration is not yet aware of it. If this is a problem"
                    " you can increase the value of 'refresh_infrastructure_cache_interval'.",
                    results_per_mor.entity,
                )
                continue
            self.log.debug(
                "Retrieved mor props for entity %s: %s",
                results_per_mor.entity,
                mor_props,
            )
            resource_type = type(results_per_mor.entity)
            metadata = self.metrics_metadata_cache.get_metadata(resource_type)
            for result in results_per_mor.value:
                metric_name = metadata.get(result.id.counterId)
                if self.log.isEnabledFor(logging.DEBUG):
                    # Use isEnabledFor to avoid unnecessary processing
                    self.log.debug(
                        "Processing metric `%s`: resource_type=`%s`, result=`%s`",
                        metric_name,
                        resource_type,
                        str(result).replace("\n", "\\n"),
                    )
                if not metric_name:
                    # Fail-safe
                    self.log.debug(
                        "Skipping value for counter %s, because the integration doesn't have metadata about it. If this"
                        " is a problem you can increase the value of 'refresh_metrics_metadata_cache_interval'",
                        result.id.counterId,
                    )
                    continue

                if not result.value:
                    self.log.debug("Skipping metric %s because the value is empty", to_string(metric_name))
                    continue

                # Get the most recent value that isn't negative
                valid_values = [v for v in result.value if v >= 0]
                if not valid_values:
                    self.log.debug(
                        "Skipping metric %s because the value returned by vCenter"
                        " is negative (i.e. the metric is not yet available). values: %s",
                        to_string(metric_name),
                        list(result.value),
                    )
                    continue

                tags = []
                if should_collect_per_instance_values(
                    self._config.collect_per_instance_filters, metric_name, resource_type
                ) and (metric_name in have_instance_value[resource_type]):
                    instance_value = result.id.instance
                    # When collecting per instance values, it's possible that both aggregated metric and per instance
                    # metrics are received. In that case, the metric with no instance value is skipped.
                    if not instance_value:
                        continue
                    instance_tag_key = get_mapped_instance_tag(metric_name)
                    tags.append('{}:{}'.format(instance_tag_key, instance_value))

                vsphere_tags = self.infrastructure_cache.get_mor_tags(results_per_mor.entity)
                mor_tags = mor_props['tags'] + vsphere_tags

                if resource_type not in HOST_RESOURCES:
                    # Tags are attached to the metrics
                    tags.extend(mor_tags)
                    hostname = None
                else:
                    # Tags are (mostly) submitted as external host tags.
                    hostname = to_string(mor_props.get('hostname'))
                    if self._config.excluded_host_tags:
                        tags.extend([t for t in mor_tags if t.split(":", 1)[0] in self._config.excluded_host_tags])

                tags.extend(self._config.base_tags)

                value = valid_values[-1]
                if metric_name in PERCENT_METRICS:
                    # Convert the percentage to a float.
                    value /= 100.0

                self.log.debug(
                    "Submit metric: name=`%s`, value=`%s`, hostname=`%s`, tags=`%s`",
                    metric_name,
                    value,
                    hostname,
                    tags,
                )
                # vSphere "rates" should be submitted as gauges (rate is precomputed).
                self.gauge(to_string(metric_name), value, hostname=hostname, tags=tags)

    def query_metrics_wrapper(self, query_specs):
        # type: (List[vim.PerformanceManager.QuerySpec]) -> List[vim.PerformanceManager.EntityMetricBase]
        """Just an instrumentation wrapper around the VSphereAPI.query_metrics method
        Warning: called in threads
        """
        t0 = Timer()
        metrics_values = self.api.query_metrics(query_specs)
        self.histogram(
            'datadog.vsphere.query_metrics.time',
            t0.total(),
            tags=self._config.base_tags,
            raw=True,
            hostname=self._hostname,
        )
        return metrics_values

    def make_query_specs(self):
        # type: () -> Iterable[List[vim.PerformanceManager.QuerySpec]]
        """
        Build query specs using MORs and metrics metadata.
        """
        server_current_time = self.api.get_current_time()
        self.log.debug("Server current datetime: %s", server_current_time)
        for resource_type in self._config.collected_resource_types:
            for metric_type in self._config.collected_metric_types:
                mors = self.infrastructure_cache.get_mors(resource_type)
                counters = self.metrics_metadata_cache.get_metadata(resource_type)
                metric_ids = []  # type: List[vim.PerformanceManager.MetricId]
                is_historical_batch = metric_type == HISTORICAL
                for counter_key, metric_name in counters.items():
                    # PerformanceManager.MetricId `instance` kwarg:
                    # - An asterisk (*) to specify all instances of the metric for the specified counterId
                    # - Double-quotes ("") to specify aggregated statistics
                    # More info https://code.vmware.com/apis/704/vsphere/vim.PerformanceManager.MetricId.html
                    if should_collect_per_instance_values(
                        self._config.collect_per_instance_filters, metric_name, resource_type
                    ):
                        instance = "*"
                    else:
                        instance = ''

                    if metric_name in ALLOWED_METRICS_FOR_MOR[resource_type][metric_type]:
                        metric_ids.append(vim.PerformanceManager.MetricId(counterId=counter_key, instance=instance))

                for batch in self.make_batch(mors, metric_ids, resource_type, is_historical_batch=is_historical_batch):
                    query_specs = []
                    for mor, metrics in batch.items():
                        query_spec = vim.PerformanceManager.QuerySpec()  # type: vim.PerformanceManager.QuerySpec
                        query_spec.entity = mor
                        query_spec.metricId = metrics
                        if is_historical_batch:
                            query_spec.startTime = server_current_time - dt.timedelta(hours=2)
                        else:
                            query_spec.intervalId = REALTIME_METRICS_INTERVAL_ID
                            query_spec.maxSample = 1  # Request a single datapoint
                        query_specs.append(query_spec)
                    if query_specs:
                        yield query_specs

    def collect_metrics_async(self):
        # type: () -> None
        """Run queries in multiple threads and wait for completion."""
        tasks = []  # type: List[Any]
        try:
            for query_specs in self.make_query_specs():
                tasks.append(self.thread_pool.submit(self.query_metrics_wrapper, query_specs))
        except Exception as e:
            self.log.warning("Unable to schedule all metric collection tasks: %s", e)
        finally:
            self.log.debug("Queued all %d tasks, waiting for completion.", len(tasks))
            for future in as_completed(tasks):
                future_exc = future.exception()
                if isinstance(future_exc, vmodl.fault.InvalidArgument):
                    # The query was invalid or the resource does not have values for this metric.
                    continue
                elif future_exc is not None:
                    self.log.warning("A metric collection API call failed with the following error: %s", future_exc)
                    continue

                results = future.result()
                if not results:
                    self.log.debug("A metric collection API call did not return data.")
                    continue

                try:
                    # Callback is called in the main thread
                    self.submit_metrics_callback(results)
                except Exception as e:
                    self.log.exception(
                        "Exception '%s' raised during the submit_metrics_callback. "
                        "Ignoring the error and continuing execution.",
                        e,
                    )

    def make_batch(
        self,
        mors,  # type: Iterable[vim.ManagedEntity]
        metric_ids,  # type: List[vim.PerformanceManager.MetricId]
        resource_type,  # type: Type[vim.ManagedEntity]
        is_historical_batch=False,  # type: bool
    ):  # type: (...) -> Generator[MorBatch, None, None]
        """Iterates over mor and generate batches with a fixed number of metrics to query.
        Querying multiple resource types in the same call is error prone if we query a cluster metric. Indeed,
        cluster metrics result in an unpredictable number of internal metric queries which all count towards
        max_query_metrics. Therefore often collecting a single cluster metric can make the whole call to fail. That's
        why we should never batch cluster metrics with anything else.
        """
        # Safeguard, let's avoid collecting multiple resources in the same call
        mors_filtered = [m for m in mors if isinstance(m, resource_type)]  # type: List[vim.ManagedEntity]

        if resource_type == vim.ClusterComputeResource:
            # Cluster metrics are unpredictable and a single call can max out the limit. Always collect them one by one.
            max_batch_size = 1  # type: float
        elif not is_historical_batch or self._config.max_historical_metrics < 0:
            # Queries are not limited by vCenter
            max_batch_size = self._config.metrics_per_query
        else:
            # Collection is limited by the value of `max_query_metrics`
            if self._config.metrics_per_query < 0:
                max_batch_size = self._config.max_historical_metrics
            else:
                max_batch_size = min(self._config.metrics_per_query, self._config.max_historical_metrics)

        batch = defaultdict(list)  # type: MorBatch
        batch_size = 0
        for m in mors_filtered:
            for metric_id in metric_ids:
                if batch_size == max_batch_size:
                    yield batch
                    batch = defaultdict(list)
                    batch_size = 0
                batch[m].append(metric_id)
                batch_size += 1
        # Do not yield an empty batch
        if batch:
            yield batch

    def submit_external_host_tags(self):
        # type: () -> None
        """Send external host tags to the Datadog backend. This is only useful for a REALTIME instance because
        only VMs and Hosts appear as 'datadog hosts'."""
        external_host_tags = []

        for resource_type in HOST_RESOURCES:
            for mor in self.infrastructure_cache.get_mors(resource_type):
                mor_props = self.infrastructure_cache.get_mor_props(mor)
                mor_tags = self.infrastructure_cache.get_mor_tags(mor)
                hostname = mor_props.get('hostname')
                # Safeguard if some mors have a None hostname
                if not hostname:
                    continue

                mor_tags = mor_props['tags'] + mor_tags
                tags = [t for t in mor_tags if t.split(':')[0] not in self._config.excluded_host_tags]
                tags.extend(self._config.base_tags)
                self.log.debug("Submitting host tags for %s: %s", hostname, tags)
                external_host_tags.append((hostname, {self.__NAMESPACE__: tags}))

        if external_host_tags:
            self.set_external_tags(external_host_tags)

    def collect_events(self):
        # type: () -> None
        self.log.debug("Starting events collection (query start time: %s).", self.latest_event_query)
        latest_event_time = None
        collect_start_time = get_current_datetime()
        try:
            t0 = Timer()
            new_events = self.api.get_new_events(start_time=self.latest_event_query)
            self.gauge(
                'datadog.vsphere.collect_events.time',
                t0.total(),
                tags=self._config.base_tags,
                raw=True,
                hostname=self._hostname,
            )
            self.log.debug("Got %s new events from the vCenter event manager", len(new_events))
            event_config = {'collect_vcenter_alarms': True}
            for event in new_events:
                self.log.debug(
                    "Processing event with id:%s, type:%s: msg:%s", event.key, type(event), event.fullFormattedMessage
                )
                normalized_event = VSphereEvent(
                    event,
                    event_config,
                    self._config.base_tags,
                    self._config.event_resource_filters,
                    self._config.exclude_filters,
                )
                # Can return None if the event if filtered out
                event_payload = normalized_event.get_datadog_payload()
                if event_payload is not None:
                    self.log.debug(
                        "Submit event with id:%s, type:%s: msg:%s", event.key, type(event), event.fullFormattedMessage
                    )
                    self.event(event_payload)
                if latest_event_time is None or event.createdTime > latest_event_time:
                    latest_event_time = event.createdTime
        except Exception as e:
            # Don't get stuck on a failure to fetch an event
            # Ignore them for next pass
            self.log.warning("Unable to fetch Events %s", e)

        if latest_event_time is not None:
            self.latest_event_query = latest_event_time + dt.timedelta(seconds=1)
        else:
            # Let's set `self.latest_event_query` to `collect_start_time` as safeguard in case no events are reported
            # OR something bad happened (which might happen again indefinitely).
            self.latest_event_query = collect_start_time

    def submit_property_metric(
        self,
        metric_name,  # type: str
        metric_value,  # type: Any
        base_tags,  # type: List[str]
        hostname,  # type: str
        resource_metric_suffix,  # type: str
        additional_tags=None,  # type: Optional[Dict[str, Optional[Any]]]
    ):
        # type: (...) -> None
        """
        Submits a property metric:
        - If the metric is a count metric (expecting tag data)
            1. Check if should have any tags added (metric value)
            2. Add the tag
            3. If there are still no valuable tags/data, then discard the metric
            4. Submit the metric as a count
        - If the metric is a guage
            1. Convert value to a float
            2. Discard if there is no float data

        Then combine all tags and submit the metric.
        """
        metric_full_name = "{}.{}".format(resource_metric_suffix, metric_name)

        if metric_full_name not in self._config.property_metrics_to_collect_by_mor.get(resource_metric_suffix, []):
            return

        is_count_metric = metric_name in PROPERTY_COUNT_METRICS

        if additional_tags is None:
            additional_tags = {}

        if is_count_metric:
            is_bool_metric = isinstance(metric_value, bool)
            no_additional_tags = all(tag is None for tag in additional_tags.values())
            if no_additional_tags:
                if metric_value is None:
                    self.log.debug(
                        "Could not submit property metric- no metric data: name=`%s`, value=`%s`, hostname=`%s`, "
                        "base tags=`%s` additional tags=`%s`, is_bool_metric=`%s`",
                        metric_full_name,
                        metric_value,
                        hostname,
                        base_tags,
                        additional_tags,
                        is_bool_metric,
                    )
                    return

                _, _, tag_name = metric_name.rpartition('.')
                property_tag = {tag_name: metric_value}
                additional_tags.update(property_tag)

            if not is_bool_metric:
                metric_value = 1

        else:
            try:
                metric_value = float(metric_value)
            except Exception:
                self.log.debug(
                    "Could not submit property metric- unexpected metric value: name=`%s`, value=`%s`, hostname=`%s`, "
                    "base tags=`%s` additional tags=`%s`",
                    metric_full_name,
                    metric_value,
                    hostname,
                    base_tags,
                    additional_tags,
                )
                return

        tags = []  # type: List[str]
        tags = tags + base_tags

        add_additional_tags(tags, additional_tags)

        # Use isEnabledFor to avoid unnecessary processing
        if self.log.isEnabledFor(logging.DEBUG):
            self.log.debug(
                "Submit property metric: name=`%s`, value=`%s`, hostname=`%s`, tags=`%s`, count=`%s`",
                metric_full_name,
                metric_value,
                hostname,
                tags,
                is_count_metric,
            )
        metric_method = self.count if is_count_metric else self.gauge
        metric_method(metric_full_name, metric_value, tags=tags, hostname=hostname)

    def submit_disk_property_metrics(
        self,
        disks,  # type: List[VmomiObject]
        base_tags,  # type: List[str]
        hostname,  # type: str
        resource_metric_suffix,  # type: str
    ):
        # type: (...) -> None
        for disk in disks:
            disk_path = disk.diskPath
            file_system_type = disk.filesystemType
            free_space = disk.freeSpace
            capacity = disk.capacity
            disk_tags = {'disk_path': disk_path, 'file_system_type': file_system_type}

            self.submit_property_metric(
                'guest.disk.freeSpace',
                free_space,
                base_tags,
                hostname,
                resource_metric_suffix,
                additional_tags=disk_tags,
            )
            self.submit_property_metric(
                'guest.disk.capacity',
                capacity,
                base_tags,
                hostname,
                resource_metric_suffix,
                additional_tags=disk_tags,
            )

    def submit_nic_property_metrics(
        self,
        nics,  # type: List[VmomiObject]
        base_tags,  # type: List[str]
        hostname,  # type: str
        resource_metric_suffix,  # type: str
    ):
        # type: (...) -> None
        for nic in nics:
            device_id = nic.deviceConfigId
            is_connected = nic.connected
            mac_address = nic.macAddress
            nic_tags = {'device_id': device_id, 'is_connected': is_connected, 'nic_mac_address': mac_address}
            self.submit_property_metric(
                'guest.net', 1, base_tags, hostname, resource_metric_suffix, additional_tags=nic_tags
            )
            if nic.ipConfig is not None:
                ip_addresses = nic.ipConfig.ipAddress
                for ip_address in ip_addresses:
                    nic_tags['nic_ip_address'] = ip_address.ipAddress
                    self.submit_property_metric(
                        'guest.net.ipConfig.address',
                        1,
                        base_tags,
                        hostname,
                        resource_metric_suffix,
                        additional_tags=nic_tags,
                    )

    def submit_ip_stack_property_metrics(
        self,
        ip_stacks,  # type: List[VmomiObject]
        base_tags,  # type: List[str]
        hostname,  # type: str
        resource_metric_suffix,  # type: str
    ):
        # type: (...) -> None
        for ip_stack in ip_stacks:
            ip_tags = {}
            if ip_stack.dnsConfig is not None:
                host_name = ip_stack.dnsConfig.hostName
                domain_name = ip_stack.dnsConfig.domainName
                ip_tags.update({'route_hostname': host_name, 'route_domain_name': domain_name})

            if ip_stack.ipRouteConfig is not None:
                ip_routes = ip_stack.ipRouteConfig.ipRoute
                for ip_route in ip_routes:
                    prefix_length = ip_route.prefixLength
                    network = ip_route.network

                    route_tags = {
                        'network_dest_ip': network,
                        'prefix_length': prefix_length,
                    }

                    if ip_route.gateway:
                        gateway_address = ip_route.gateway.ipAddress
                        device = ip_route.gateway.device
                        gateway_tags = {'device': device, 'gateway_address': gateway_address}
                        route_tags.update(gateway_tags)

                    ip_tags.update(route_tags)

                    self.submit_property_metric(
                        'guest.ipStack.ipRoute',
                        1,
                        base_tags,
                        hostname,
                        resource_metric_suffix,
                        additional_tags=ip_tags,
                    )

    def submit_simple_property_metrics(
        self,
        all_properties,  # type: Dict[str, Any]
        base_tags,  # type: List[str]
        hostname,  # type: str
        resource_metric_suffix,  # type: str
    ):
        # type: (...) -> None
        simple_properties = self._config.simple_properties_to_collect_by_mor.get(resource_metric_suffix, [])
        for property_name in simple_properties:
            property_val = all_properties.get(property_name, None)

            self.submit_property_metric(
                property_name,
                property_val,
                base_tags,
                hostname,
                resource_metric_suffix,
            )

    def submit_property_metrics(
        self,
        resource_type,  # type: Type[vim.ManagedEntity]
        mor_props,  # type: Dict[str, Any]
        resource_tags,  # type: List[str]
    ):
        # type: (...) -> None
        resource_metric_suffix = MOR_TYPE_AS_STRING[resource_type]
        mor_name = to_string(mor_props.get('name', 'unknown'))
        hostname = mor_props.get('hostname', 'unknown')

        all_properties = mor_props.get('properties', None)
        if not all_properties:
            self.log.debug(
                'Could not retrieve properties for %s resource %s hostname=%s',
                resource_metric_suffix,
                mor_name,
                hostname,
            )
            return

        base_tags = []
        if self._config.excluded_host_tags:
            base_tags.extend([t for t in resource_tags if t.split(":", 1)[0] in self._config.excluded_host_tags])
        else:
            base_tags.extend(resource_tags)
        base_tags.extend(self._config.base_tags)

        if resource_type == vim.VirtualMachine:
            object_properties = self._config.object_properties_to_collect_by_mor.get(resource_metric_suffix, [])

            net_property = 'guest.net'
            if net_property in object_properties:
                nics = all_properties.get('guest.net', [])
                self.submit_nic_property_metrics(nics, base_tags, hostname, resource_metric_suffix)

            ip_stack_property = 'guest.ipStack'
            if net_property in object_properties:
                ip_stacks = all_properties.get(ip_stack_property, [])
                self.submit_ip_stack_property_metrics(ip_stacks, base_tags, hostname, resource_metric_suffix)

            disk_property = 'guest.disk'
            if disk_property in object_properties:
                disks = all_properties.get(disk_property, [])
                self.submit_disk_property_metrics(disks, base_tags, hostname, resource_metric_suffix)

        self.submit_simple_property_metrics(all_properties, base_tags, hostname, resource_metric_suffix)

    def check(self, _):
        # type: (Any) -> None
        self._hostname = datadog_agent.get_hostname()
        # Assert the health of the vCenter API by getting the version, and submit the service_check accordingly

        now = get_timestamp()
        if self.last_connection_time + self._config.connection_reset_timeout <= now or self.api is None:
            self.last_connection_time = now
            self.log.debug("Refreshing vCenter connection")
            self.initiate_api_connection()

        try:
            version_info = self.api.get_version()
            if self.is_metadata_collection_enabled():
                self.set_metadata('version', version_info.version_str)
        except Exception:
            # Explicitly do not attach any host to the service checks.
            self.log.exception("The vCenter API is not responding. The check will not run.")
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self._config.base_tags, hostname=None)
            raise
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self._config.base_tags, hostname=None)

        # Collect and submit events
        if self._config.should_collect_events:
            self.collect_events()

        if self._config.collect_events_only:
            return

        # Update the value of `max_query_metrics` if needed
        if self._config.is_historical():
            try:
                vcenter_max_hist_metrics = self.api.get_max_query_metrics()
                if (vcenter_max_hist_metrics < self._config.max_historical_metrics) or (
                    self._config.max_historical_metrics < 0
                    and vcenter_max_hist_metrics != UNLIMITED_HIST_METRICS_PER_QUERY
                ):
                    self.log.warning(
                        "The integration was configured with `max_historical_metrics: %d` but your vCenter has a"
                        "limit of %d which is lower. Ignoring your configuration in favor of the vCenter value."
                        "To update the vCenter value, please update the `%s` field",
                        self._config.max_historical_metrics,
                        vcenter_max_hist_metrics,
                        MAX_QUERY_METRICS_OPTION,
                    )
                    self._config.max_historical_metrics = vcenter_max_hist_metrics
            except Exception:
                self._config.max_historical_metrics = DEFAULT_MAX_QUERY_METRICS
                self.log.info(
                    "Could not fetch the value of %s, setting `max_historical_metrics` to %d.",
                    MAX_QUERY_METRICS_OPTION,
                    DEFAULT_MAX_QUERY_METRICS,
                )
                pass

        # Refresh the metrics metadata cache
        if self.metrics_metadata_cache.is_expired():
            with self.metrics_metadata_cache.update():
                self.refresh_metrics_metadata_cache()

        # Refresh the infrastructure cache
        if self.infrastructure_cache.is_expired():
            with self.infrastructure_cache.update():
                self.refresh_infrastructure_cache()

            # Submit host tags as soon as we have fresh data
            self.submit_external_host_tags()

            # Submit property metrics after the cache is refreshed
            if self._config.collect_property_metrics:

                resources_with_property_metrics = [
                    resource
                    for resource in self._config.collected_resource_types
                    if MOR_TYPE_AS_STRING[resource] in PROPERTY_METRICS_BY_RESOURCE_TYPE.keys()
                ]

                for resource_type in resources_with_property_metrics:
                    for mor in self.infrastructure_cache.get_mors(resource_type):
                        mor_props = self.infrastructure_cache.get_mor_props(mor)
                        resource_tags = mor_props.get('tags', [])
                        self.submit_property_metrics(resource_type, mor_props, resource_tags)
                # delete property data from the cache since it won't be used until next cache refresh
                self.infrastructure_cache.clear_properties()

        # Submit the number of resources that are monitored
        for resource_type in self._config.collected_resource_types:
            for mor in self.infrastructure_cache.get_mors(resource_type):
                mor_props = self.infrastructure_cache.get_mor_props(mor)
                # Explicitly do not attach any host to those metrics.
                resource_tags = mor_props.get('tags', [])
                self.count(
                    '{}.count'.format(MOR_TYPE_AS_STRING[resource_type]),
                    1,
                    tags=self._config.base_tags + resource_tags,
                    hostname=None,
                )

        # Creating a thread pool and starting metric collection
        self.log.debug("Starting metric collection in %d threads.", self._config.threads_count)
        self.collect_metrics_async()
        self.log.debug("Metric collection completed.")
