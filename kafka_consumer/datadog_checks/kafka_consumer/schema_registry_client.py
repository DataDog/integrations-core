# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


class SchemaRegistryClient:
    def __init__(self, config, log, http):
        self.config = config
        self.log = log
        self.http = http
        self._configure_http_client()

    def _configure_http_client(self):
        """Configure the HTTP client with authentication and TLS settings."""
        # Configure basic authentication if username/password provided
        if self.config._schema_registry_username and self.config._schema_registry_password:
            self.log.debug("Configuring Schema Registry with Basic Authentication")
            self.http.options['auth'] = (
                self.config._schema_registry_username,
                self.config._schema_registry_password,
            )

        # Configure TLS verification
        if not self.config._schema_registry_tls_verify:
            self.log.debug("Schema Registry TLS verification is disabled")
            self.http.options['verify'] = False
        elif self.config._schema_registry_tls_ca_cert:
            self.log.debug("Using custom CA certificate for Schema Registry")
            self.http.options['verify'] = self.config._schema_registry_tls_ca_cert
        else:
            self.http.options['verify'] = True

        # Configure client certificate authentication if provided
        if self.config._schema_registry_tls_cert and self.config._schema_registry_tls_key:
            self.log.debug("Configuring Schema Registry with client certificate authentication")
            self.http.options['cert'] = (
                self.config._schema_registry_tls_cert,
                self.config._schema_registry_tls_key,
            )
        elif self.config._schema_registry_tls_cert:
            # If only cert is provided without key
            self.http.options['cert'] = self.config._schema_registry_tls_cert

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
