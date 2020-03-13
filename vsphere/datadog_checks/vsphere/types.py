from typing import Dict, List, Optional, Pattern, Tuple, TypedDict

# CONFIG ALIASES
from vim import ManagedEntity, ManagedEntityType, PerformanceManager

ResourceFilterConfig = TypedDict('ResourceFilterConfig', {'resource': str, 'property': str, 'patterns': List[str]})
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
        'collect_events': bool,
        'collect_tags': bool,
        'tags_prefix': str,
        'excluded_host_tags': List[str],
        'tags': List[str],
        'refresh_infrastructure_cache_interval': int,
        'refresh_metrics_metadata_cache_interval': int,
        'refresh_tags_cache_interval': int,
        'resource_filters': List[ResourceFilterConfig],
        'metric_filters': MetricFilterConfig,
        'collect_per_instance_filters': MetricFilterConfig,
    },
)

# CHECK ALIASES
MetricName = str

InfrastructureDataItem = TypedDict(
    'InfrastructureDataItem',
    {
        'name': str,
        'runtime.host': ManagedEntity,
        'guest.hostName': str,
        'runtime.powerState': str,
        'parent': Optional[ManagedEntity],
    },
    total=False,
)
InfrastructureData = Dict[ManagedEntity, InfrastructureDataItem]

MorBatch = Dict[ManagedEntity, List[PerformanceManager.MetricId]]

ResourceTags = Dict[ManagedEntityType, Dict[str, List[str]]]

TagAssociation = TypedDict('TagAssociation', {'tag_id': str, 'object_ids': List[Dict[str, str]]})

ResourceFilters = Dict[Tuple[str, str], List[Pattern]]
MetricFilters = Dict[str, List[Pattern]]
CounterId = int
