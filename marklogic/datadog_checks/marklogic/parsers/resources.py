# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from typing import Any, Dict, List  # noqa: F401

from ..constants import BASE_ENDPOINT, RESOURCE_TYPES


def parse_resources(data):
    # type: (Dict[str, Any]) -> List[Dict[str, str]]
    resources = []  # type: List[Dict[str, str]]

    for group in data['cluster-query']['relations']['relation-group']:
        resource_type = group['typeref']
        for rel in group['relation']:
            resource_found = {
                'id': rel['idref'],
                'type': RESOURCE_TYPES[resource_type]['singular'],
                'name': rel['nameref'],
                'uri': rel['uriref'][len(BASE_ENDPOINT) :],
            }

            if rel.get('qualifiers'):
                # Making sure the group-id is in the qualifiers
                for qualifier in rel['qualifiers']['qualifier']:
                    if 'group-id={}'.format(qualifier['nameref']) in rel['uriref']:
                        resource_found['group'] = qualifier['nameref']
                        break
            resources.append(resource_found)

    return resources
