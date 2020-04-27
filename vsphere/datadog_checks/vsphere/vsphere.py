# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
from __future__ import division

import datetime as dt
from collections import defaultdict
from concurrent.futures import as_completed
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Any, Dict, Generator, Iterable, List, Set, Type, cast

from pyVmomi import vim, vmodl
from six import iteritems

from datadog_checks.base import AgentCheck, is_affirmative, to_string
from datadog_checks.base.checks.libs.timer import Timer
from datadog_checks.vsphere.api import APIConnectionError, VSphereAPI
from datadog_checks.vsphere.api_rest import VSphereRestAPI
from datadog_checks.vsphere.cache import InfrastructureCache, MetricsMetadataCache
from datadog_checks.vsphere.config import VSphereConfig
from datadog_checks.vsphere.constants import (
    DEFAULT_MAX_QUERY_METRICS,
    HISTORICAL_RESOURCES,
    MAX_QUERY_METRICS_OPTION,
    REALTIME_METRICS_INTERVAL_ID,
    REALTIME_RESOURCES,
)
from datadog_checks.vsphere.legacy.event import VSphereEvent
from datadog_checks.vsphere.metrics import ALLOWED_METRICS_FOR_MOR, PERCENT_METRICS
from datadog_checks.vsphere.resource_filters import TagFilter
from datadog_checks.vsphere.types import (
    CounterId,
    InfrastructureData,
    InstanceConfig,
    MetricName,
    MorBatch,
    ResourceTags,
)
from datadog_checks.vsphere.utils import (
    MOR_TYPE_AS_STRING,
    format_metric_name,
    get_mapped_instance_tag,
    get_parent_tags_recursively,
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
        self.config = VSphereConfig(instance, self.log)

        self.latest_event_query = dt.datetime.now()
        self.infrastructure_cache = InfrastructureCache(interval_sec=self.config.refresh_infrastructure_cache_interval)
        self.metrics_metadata_cache = MetricsMetadataCache(
            interval_sec=self.config.refresh_metrics_metadata_cache_interval
        )
        self.api = cast(VSphereAPI, None)
        self.api_rest = cast(VSphereRestAPI, None)
        # Do not override `AgentCheck.hostname`
        self._hostname = None
        self.thread_pool = ThreadPoolExecutor(max_workers=self.config.threads_count)
        self.check_initializations.append(self.initiate_api_connection)

    def initiate_api_connection(self):
        # type: () -> None
        try:
            self.log.debug(
                "Connecting to the vCenter API %s with username %s...", self.config.hostname, self.config.username
            )
            self.api = VSphereAPI(self.config, self.log)
            self.log.debug("Connected")
        except APIConnectionError:
            self.log.error("Cannot authenticate to vCenter API. The check will not run.")
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.config.base_tags, hostname=None)
            raise

        if self.config.should_collect_tags:
            try:
                self.api_rest = VSphereRestAPI(self.config, self.log)
            except Exception as e:
                self.log.error("Cannot connect to vCenter REST API. Tags won't be collected. Error: %s", e)

    def refresh_metrics_metadata_cache(self):
        # type: () -> None
        """
        Request the list of counters (metrics) from vSphere and store them in a cache.
        """
        self.log.debug(
            "Refreshing the metrics metadata cache. Collecting all counters metadata for collection_level=%d",
            self.config.collection_level,
        )
        t0 = Timer()
        counters = self.api.get_perf_counter_by_level(self.config.collection_level)
        self.gauge(
            "datadog.vsphere.refresh_metrics_metadata_cache.time",
            t0.total(),
            tags=self.config.base_tags,
            raw=True,
            hostname=self._hostname,
        )
        self.log.debug("Collected %d counters metadata in %.3f seconds.", len(counters), t0.total())

        for mor_type in self.config.collected_resource_types:
            allowed_counters = []
            for c in counters:
                metric_name = format_metric_name(c)
                if metric_name in ALLOWED_METRICS_FOR_MOR[mor_type] and not is_metric_excluded_by_filters(
                    metric_name, mor_type, self.config.metric_filters
                ):
                    allowed_counters.append(c)
            metadata = {c.key: format_metric_name(c) for c in allowed_counters}  # type: Dict[CounterId, MetricName]
            self.metrics_metadata_cache.set_metadata(mor_type, metadata)

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
        resource_filters_without_tags = [f for f in self.config.resource_filters if not isinstance(f, TagFilter)]
        filtered_infra_data = {
            mor: props
            for mor, props in iteritems(infrastructure_data)
            if isinstance(mor, tuple(self.config.collected_resource_types))
            and is_resource_collected_by_filters(mor, infrastructure_data, resource_filters_without_tags)
        }

        t0 = Timer()
        mors_list = list(filtered_infra_data.keys())
        try:
            mor_tags = self.api_rest.get_resource_tags_for_mors(mors_list)
        except Exception as e:
            self.log.error("Failed to collect tags: %s", e)
            return {}

        self.gauge('datadog.vsphere.query_tags.time', t0.total(), tags=self.config.base_tags, raw=True)
        return mor_tags

    def refresh_infrastructure_cache(self):
        # type: () -> None
        """Fetch the complete infrastructure, generate tags for each monitored resources and store all of that
        into the infrastructure_cache. It also computes the resource `hostname` property to be used when submitting
        metrics for this mor."""
        self.log.debug("Refreshing the infrastructure cache...")
        t0 = Timer()
        infrastructure_data = self.api.get_infrastructure()
        self.gauge(
            "datadog.vsphere.refresh_infrastructure_cache.time",
            t0.total(),
            tags=self.config.base_tags,
            raw=True,
            hostname=self._hostname,
        )
        self.log.debug("Infrastructure cache refreshed in %.3f seconds.", t0.total())

        all_tags = {}
        if self.config.should_collect_tags:
            all_tags = self.collect_tags(infrastructure_data)
        self.infrastructure_cache.set_all_tags(all_tags)

        for mor, properties in iteritems(infrastructure_data):
            if not isinstance(mor, tuple(self.config.collected_resource_types)):
                # Do nothing for the resource types we do not collect
                continue

            if not is_resource_collected_by_filters(
                mor, infrastructure_data, self.config.resource_filters, self.infrastructure_cache.get_mor_tags(mor)
            ):
                # The resource does not match the specified whitelist/blacklist patterns.
                continue

            mor_name = to_string(properties.get("name", "unknown"))
            mor_type_str = MOR_TYPE_AS_STRING[type(mor)]
            hostname = None
            tags = []

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
                runtime_host_props = infrastructure_data[runtime_host] if runtime_host else {}
                runtime_hostname = to_string(runtime_host_props.get("name", "unknown"))
                tags.append('vsphere_host:{}'.format(runtime_hostname))

                if self.config.use_guest_hostname:
                    hostname = properties.get("guest.hostName", mor_name)
                else:
                    hostname = mor_name
            elif isinstance(mor, vim.HostSystem):
                hostname = mor_name
            else:
                tags.append('vsphere_{}:{}'.format(mor_type_str, mor_name))

            tags.extend(get_parent_tags_recursively(mor, infrastructure_data))
            tags.append('vsphere_type:{}'.format(mor_type_str))
            mor_payload = {"tags": tags}  # type: Dict[str, Any]

            if hostname:
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
                    have_instance_value[resource_type].add(metadata[result.id.counterId])

        for results_per_mor in query_results:
            mor_props = self.infrastructure_cache.get_mor_props(results_per_mor.entity)
            if mor_props is None:
                self.log.debug(
                    "Skipping results for mor %s because the integration is not yet aware of it. If this is a problem"
                    " you can increase the value of 'refresh_infrastructure_cache_interval'.",
                    results_per_mor.entity,
                )
                continue
            resource_type = type(results_per_mor.entity)
            metadata = self.metrics_metadata_cache.get_metadata(resource_type)
            for result in results_per_mor.value:
                metric_name = metadata.get(result.id.counterId)
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
                        " is negative (i.e. the metric is not yet available).",
                        to_string(metric_name),
                    )
                    continue

                tags = []
                if should_collect_per_instance_values(self.config, metric_name, resource_type) and (
                    metric_name in have_instance_value[resource_type]
                ):
                    instance_value = result.id.instance
                    # When collecting per instance values, it's possible that both aggregated metric and per instance
                    # metrics are received. In that case, the metric with no instance value is skipped.
                    if not instance_value:
                        continue
                    instance_tag_key = get_mapped_instance_tag(metric_name)
                    tags.append('{}:{}'.format(instance_tag_key, instance_value))

                vsphere_tags = self.infrastructure_cache.get_mor_tags(results_per_mor.entity)
                mor_tags = mor_props['tags'] + vsphere_tags

                if resource_type in HISTORICAL_RESOURCES:
                    # Tags are attached to the metrics
                    tags.extend(mor_tags)
                    hostname = None
                else:
                    # Tags are (mostly) submitted as external host tags.
                    hostname = to_string(mor_props.get('hostname'))
                    if self.config.excluded_host_tags:
                        tags.extend([t for t in mor_tags if t.split(":", 1)[0] in self.config.excluded_host_tags])

                tags.extend(self.config.base_tags)

                value = valid_values[-1]
                if metric_name in PERCENT_METRICS:
                    # Convert the percentage to a float.
                    value /= 100.0

                # vSphere "rates" should be submitted as gauges (rate is precomputed).
                self.gauge(to_string(metric_name), value, hostname=hostname, tags=tags)

    def query_metrics_wrapper(self, query_specs):
        # type: (List[vim.PerformanceManager.QuerySpec]) -> List[vim.PerformanceManager.EntityMetricBase]
        """Just an instrumentation wrapper around the VSphereAPI.query_metrics method
        Warning: called in threads
        """
        t0 = Timer()
        metrics_values = self.api.query_metrics(query_specs)
        self.histogram('datadog.vsphere.query_metrics.time', t0.total(), tags=self.config.base_tags, raw=True)
        return metrics_values

    def make_query_specs(self):
        # type: () -> Iterable[List[vim.PerformanceManager.QuerySpec]]
        """
        Build query specs using MORs and metrics metadata.
        """
        for resource_type in self.config.collected_resource_types:
            mors = self.infrastructure_cache.get_mors(resource_type)
            counters = self.metrics_metadata_cache.get_metadata(resource_type)
            metric_ids = []  # type: List[vim.PerformanceManager.MetricId]
            for counter_key, metric_name in iteritems(counters):
                # PerformanceManager.MetricId `instance` kwarg:
                # - An asterisk (*) to specify all instances of the metric for the specified counterId
                # - Double-quotes ("") to specify aggregated statistics
                # More info https://code.vmware.com/apis/704/vsphere/vim.PerformanceManager.MetricId.html
                if should_collect_per_instance_values(self.config, metric_name, resource_type):
                    instance = "*"
                else:
                    instance = ''

                metric_ids.append(vim.PerformanceManager.MetricId(counterId=counter_key, instance=instance))

            for batch in self.make_batch(mors, metric_ids, resource_type):
                query_specs = []
                for mor, metrics in iteritems(batch):
                    query_spec = vim.PerformanceManager.QuerySpec()  # type: vim.PerformanceManager.QuerySpec
                    query_spec.entity = mor
                    query_spec.metricId = metrics
                    if resource_type in REALTIME_RESOURCES:
                        query_spec.intervalId = REALTIME_METRICS_INTERVAL_ID
                        query_spec.maxSample = 1  # Request a single datapoint
                    else:
                        # We cannot use `maxSample` for historical metrics, let's specify a timewindow that will
                        # contain at least one element
                        query_spec.startTime = dt.datetime.now() - dt.timedelta(hours=2)
                    query_specs.append(query_spec)
                if query_specs:
                    yield query_specs

    def collect_metrics_async(self):
        # type: () -> None
        """Run queries in multiple threads and wait for completion."""
        tasks = []
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
    ):  # type: (...) -> Generator[MorBatch, None, None]
        """Iterates over mor and generate batches with a fixed number of metrics to query.
        Querying multiple resource types in the same call is error prone if we query a cluster metric. Indeed,
        cluster metrics result in an unpredicatable number of internal metric queries which all count towards
        max_query_metrics. Therefore often collecting a single cluster metric can make the whole call to fail. That's
        why we should never batch cluster metrics with anything else.
        """
        # Safeguard, let's avoid collecting multiple resources in the same call
        mors_filtered = [m for m in mors if isinstance(m, resource_type)]  # type: List[vim.ManagedEntity]

        if resource_type == vim.ClusterComputeResource:
            # Cluster metrics are unpredictable and a single call can max out the limit. Always collect them one by one.
            max_batch_size = 1  # type: float
        elif resource_type in REALTIME_RESOURCES or self.config.max_historical_metrics < 0:
            # Queries are not limited by vCenter
            max_batch_size = self.config.metrics_per_query
        else:
            # Collection is limited by the value of `max_query_metrics`
            if self.config.metrics_per_query < 0:
                max_batch_size = self.config.max_historical_metrics
            else:
                max_batch_size = min(self.config.metrics_per_query, self.config.max_historical_metrics)

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

        for resource_type in REALTIME_RESOURCES:
            for mor in self.infrastructure_cache.get_mors(resource_type):
                mor_props = self.infrastructure_cache.get_mor_props(mor)
                mor_tags = self.infrastructure_cache.get_mor_tags(mor)
                hostname = mor_props.get('hostname')
                # Safeguard if some mors have a None hostname
                if not hostname:
                    continue

                mor_tags = mor_props['tags'] + mor_tags
                tags = [t for t in mor_tags if t.split(':')[0] not in self.config.excluded_host_tags]
                tags.extend(self.config.base_tags)
                external_host_tags.append((hostname, {self.__NAMESPACE__: tags}))

        if external_host_tags:
            self.set_external_tags(external_host_tags)

    def collect_events(self):
        # type: () -> None
        self.log.debug("Starting events collection.")
        try:
            t0 = Timer()
            new_events = self.api.get_new_events(start_time=self.latest_event_query)
            self.gauge(
                'datadog.vsphere.collect_events.time',
                t0.total(),
                tags=self.config.base_tags,
                raw=True,
                hostname=self._hostname,
            )
            self.log.debug("Got %s new events from the vCenter event manager", len(new_events))
            event_config = {'collect_vcenter_alarms': True}
            for event in new_events:
                normalized_event = VSphereEvent(event, event_config, self.config.base_tags)
                # Can return None if the event if filtered out
                event_payload = normalized_event.get_datadog_payload()
                if event_payload is not None:
                    self.event(event_payload)
        except Exception as e:
            # Don't get stuck on a failure to fetch an event
            # Ignore them for next pass
            self.log.warning("Unable to fetch Events %s", e)

        self.latest_event_query = self.api.get_latest_event_timestamp() + dt.timedelta(seconds=1)

    def check(self, _):
        # type: (Any) -> None
        self._hostname = datadog_agent.get_hostname()
        # Assert the health of the vCenter API by getting the version, and submit the service_check accordingly
        try:
            version_info = self.api.get_version()
            if self.is_metadata_collection_enabled():
                self.set_metadata('version', version_info.version_str)
        except Exception:
            # Explicitly do not attach any host to the service checks.
            self.log.exception("The vCenter API is not responding. The check will not run.")
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.CRITICAL, tags=self.config.base_tags, hostname=None)
            raise
        else:
            self.service_check(SERVICE_CHECK_NAME, AgentCheck.OK, tags=self.config.base_tags, hostname=None)

        # Update the value of `max_query_metrics` if needed
        if self.config.is_historical():
            try:
                vcenter_max_hist_metrics = self.api.get_max_query_metrics()
                if vcenter_max_hist_metrics < self.config.max_historical_metrics:
                    self.log.warning(
                        "The integration was configured with `max_query_metrics: %d` but your vCenter has a"
                        "limit of %d which is lower. Ignoring your configuration in favor of the vCenter value."
                        "To update the vCenter value, please update the `%s` field",
                        self.config.max_historical_metrics,
                        vcenter_max_hist_metrics,
                        MAX_QUERY_METRICS_OPTION,
                    )
                    self.config.max_historical_metrics = vcenter_max_hist_metrics
            except Exception:
                self.config.max_historical_metrics = DEFAULT_MAX_QUERY_METRICS
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

        # Collect and submit events
        if self.config.should_collect_events:
            self.collect_events()

        # Submit the number of VMs that are monitored
        for resource_type in self.config.collected_resource_types:
            for mor in self.infrastructure_cache.get_mors(resource_type):
                mor_props = self.infrastructure_cache.get_mor_props(mor)
                # Explicitly do not attach any host to those metrics.
                resource_tags = mor_props.get('tags', [])
                self.count(
                    '{}.count'.format(MOR_TYPE_AS_STRING[resource_type]),
                    1,
                    tags=self.config.base_tags + resource_tags,
                    hostname=None,
                )

        # Creating a thread pool and starting metric collection
        self.log.debug("Starting metric collection in %d threads.", self.config.threads_count)
        self.collect_metrics_async()
        self.log.debug("Metric collection completed.")
