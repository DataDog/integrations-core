# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Any, Dict, List, Optional, Pattern, Type, TypedDict

# CONFIG ALIASES
from pyVmomi import VmomiSupport, vim

ResourceFilterConfig = TypedDict(
    'ResourceFilterConfig', {'resource': str, 'property': str, 'type': str, 'patterns': List[str]}
)
MetricFilterConfig = Dict[str, List[str]]

InstanceConfig = TypedDict(
    'InstanceConfig',
    {
        'host': str,
        'username': str,
        'password': str,
        'ssl_verify': bool,
        'ssl_capath': str,
        'tls_ignore_warning': bool,
        'collection_level': int,
        'collection_type': str,
        'use_guest_hostname': bool,
        'max_historical_metrics': int,
        'threads_count': int,
        'metrics_per_query': int,
        'batch_property_collector_size': int,
        'batch_tags_collector_size': int,
        'collect_events': bool,
        'use_collect_events_fallback': bool,
        'collect_events_only': bool,
        'collect_tags': bool,
        'tags_prefix': str,
        'collect_attributes': bool,
        'attributes_prefix': bool,
        'excluded_host_tags': List[str],
        'tags': List[str],
        'refresh_infrastructure_cache_interval': int,
        'refresh_metrics_metadata_cache_interval': int,
        'resource_filters': List[ResourceFilterConfig],
        'metric_filters': MetricFilterConfig,
        'collect_per_instance_filters': MetricFilterConfig,
        'include_datastore_cluster_folder_tag': bool,
        'rest_api_options': Dict[str, Any],
    },
)

# CHECK ALIASES
MetricName = str
CounterId = int

VmomiObject = VmomiSupport.Object

InfrastructureDataItem = TypedDict(
    'InfrastructureDataItem',
    {
        'name': str,
        'runtime.host': vim.ManagedEntity,
        'guest.hostName': str,
        'runtime.powerState': str,
        'summary.config.numCpu': int,
        'summary.config.memorySizeMB': int,
        'summary.config.numEthernetCards': int,
        'summary.config.numVirtualDisks': int,
        'summary.quickStats.uptimeSeconds': int,
        'guest.guestFullName': str,
        'guest.disk': List[VmomiObject],
        'guest.net': List[VmomiObject],
        'guest.ipStack': List[VmomiObject],
        'guest.toolsRunningStatus': str,
        'guest.toolsVersionStatus2': str,
        'guest.toolsVersion': str,
        'config.hardware.numCoresPerSocket': str,
        'parent': Optional[vim.ManagedEntity],
        'attributes': List[str],
    },
    total=False,
)
InfrastructureData = Dict[vim.ManagedEntity, InfrastructureDataItem]

ResourceTags = Dict[Type[vim.ManagedEntity], Dict[str, List[str]]]
TagAssociation = TypedDict('TagAssociation', {'object_id': Dict[str, str], 'tag_ids': List[str]})

MetricFilters = Dict[str, List[Pattern]]

MorBatch = Dict[vim.ManagedEntity, List[vim.PerformanceManager.MetricId]]
