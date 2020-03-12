from typing import Any, Dict, List, TypedDict

# parent is a MOR resource
InfrastructureDataItem = TypedDict('InfrastructureDataItem', {'name': str, 'parent': Any})

ResourceTags = Dict[Any, Dict[str, List]]

TagAssociation = TypedDict('TagAssociation', {'tag_id': str, 'object_ids': List[Dict[str, str]]})
