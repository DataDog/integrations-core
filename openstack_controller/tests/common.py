# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)


E2E_METADATA = {
    'start_commands': [
        # Need new version of pip to upgrade setuptools...
        'pip install openstacksdk==4.7.0'
    ]
}


def remove_service_from_catalog(d, services):
    catalog = d.get('token', {}).get('catalog', {})
    new_catalog = []
    for service in catalog:
        if service['type'] not in services:
            new_catalog.append(service)
    return {**d, **{'token': {**d['token'], 'catalog': new_catalog}}}
