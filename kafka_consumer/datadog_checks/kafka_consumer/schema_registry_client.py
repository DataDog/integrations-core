# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class SchemaRegistryClient:
    def __init__(self, config, log, http):
        self.config = config
        self.log = log
        self.http = http

    def get_subjects(self):
        """Fetch all subjects from the Schema Registry."""
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/subjects")
        response.raise_for_status()
        return response.json()

    def get_versions(self, subject):
        """Fetch all versions for a given subject."""
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/subjects/{subject}/versions")
        response.raise_for_status()
        return response.json()

    def get_latest_version(self, subject):
        """Fetch the latest version details for a given subject."""
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/subjects/{subject}/versions/latest")
        response.raise_for_status()
        return response.json()
