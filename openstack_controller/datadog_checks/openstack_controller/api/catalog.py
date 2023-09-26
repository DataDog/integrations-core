# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class Catalog:
    def __init__(self, catalog, endpoint_interface, endpoint_region_id):
        self.catalog = catalog
        self.endpoint_interface = endpoint_interface
        self.endpoint_region_id = endpoint_region_id

    def has_component(self, component_type):
        for service in self.catalog:
            if service['type'] == component_type:
                return True
        return False

    def get_endpoint_by_type(self, endpoint_type):
        for item in self.catalog:
            if item['type'] == endpoint_type:
                for endpoint in item['endpoints']:
                    if endpoint['interface'] == self.endpoint_interface and (
                        self.endpoint_region_id is None or endpoint['region_id'] == self.endpoint_region_id
                    ):
                        return endpoint['url']
        return None
