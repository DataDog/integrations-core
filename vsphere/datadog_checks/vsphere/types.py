from typing import Any, Dict, List, Pattern, Tuple, TypedDict

MorObject = Any
MorType = Any
Counter = Any


# parent is a MOR resource
InfrastructureDataItem = TypedDict('InfrastructureDataItem', {
    'name': str,
    'runtime.host': str,
    'guest.hostName': str,
    'parent': Any
})
InfrastructureData = Dict[MorType, InfrastructureDataItem]

ResourceTags = Dict[Any, Dict[str, List]]

TagAssociation = TypedDict('TagAssociation', {'tag_id': str, 'object_ids': List[Dict[str, str]]})

ResourceFilterConfig = TypedDict('ResourceFilterConfig', {'resource': str, 'property': str, 'patterns': List[str]})
MetricFilterConfig = Dict[str, List[str]]

FormattedResourceFilter = Dict[Tuple[str, str], List[Pattern]]
FormattedMetricFilters = Dict[str, List[Pattern]]
