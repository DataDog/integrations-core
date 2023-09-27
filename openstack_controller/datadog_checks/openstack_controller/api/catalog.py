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

    def get_endpoint_by_type(self, endpoint_types):
        for item in self.catalog:
            if item['type'] in endpoint_types:
                for endpoint in item['endpoints']:
                    matched_interface = (
                        endpoint['interface'] == 'public'
                        if not self.endpoint_interface
                        else endpoint['interface'] == self.endpoint_interface
                    )
                    if matched_interface and (
                        not self.endpoint_region_id or endpoint['region_id'] == self.endpoint_region_id
                    ):
                        return endpoint['url']
        return None
