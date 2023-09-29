# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class Catalog:
    def __init__(self, catalog, endpoint_interface, endpoint_region_id):
        self.catalog = catalog
        self.endpoint_interface = endpoint_interface
        self.endpoint_region_id = endpoint_region_id

    def has_component(self, component_types):
        for service in self.catalog:
            if service['type'] in component_types:
                return True
        return False

    def get_endpoint_by_type(self, service_types):
        for service_type in service_types:
            for service in self.catalog:
                if service.get('type') == service_type:
                    for endpoint in service.get('endpoints', []):
                        endpoint_interface = endpoint.get('interface')
                        endpoint_region_id = endpoint.get('region_id')
                        matched_interface = (
                            endpoint_interface == 'public'
                            if not self.endpoint_interface
                            else endpoint_interface == self.endpoint_interface
                        )
                        matched_region_id = not self.endpoint_region_id or endpoint_region_id == self.endpoint_region_id
                        if matched_interface and matched_region_id:
                            return endpoint['url']
        return None
