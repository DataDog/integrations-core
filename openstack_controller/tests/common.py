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


def version_identity_endpoints(d):
    catalog = []
    for service in d.get('token', {}).get('catalog', []):
        if service['type'] == 'identity':
            endpoints = [{**endpoint, 'url': endpoint['url'] + '/v3'} for endpoint in service['endpoints']]
            service = {**service, 'endpoints': endpoints}
        catalog.append(service)
    return {**d, **{'token': {**d['token'], 'catalog': catalog}}}
