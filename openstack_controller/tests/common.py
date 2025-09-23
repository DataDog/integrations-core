# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


def remove_service_from_catalog(d, services):
    catalog = d.get('token', {}).get('catalog', {})
    new_catalog = []
    for service in catalog:
        if service['type'] not in services:
            new_catalog.append(service)
    return {**d, **{'token': {**d['token'], 'catalog': new_catalog}}}
