# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Schema Registry client with authentication support."""


class SchemaRegistryClient:
    """Client for interacting with Confluent Schema Registry."""

    def __init__(self, config: dict, log, http):
        """Initialize Schema Registry client.

        Args:
            config: Configuration dict with schema_registry_* parameters
            log: Logger instance
            http: HTTP client (from AgentCheck.http)
        """
        self.config = config
        self.log = log
        self.http = http
        self._configure_http_client()

    def _configure_http_client(self):
        """Configure the HTTP client with authentication and TLS settings."""
        # Configure basic authentication if username/password provided
        if self.config.get('schema_registry_username') and self.config.get('schema_registry_password'):
            self.log.debug("Configuring Schema Registry with Basic Authentication")
            self.http.options['auth'] = (
                self.config['schema_registry_username'],
                self.config['schema_registry_password'],
            )

        # Configure TLS verification
        if not self.config.get('schema_registry_tls_verify', True):
            self.log.debug("Schema Registry TLS verification is disabled")
            self.http.options['verify'] = False
        elif self.config.get('schema_registry_tls_ca_cert'):
            self.log.debug("Using custom CA certificate for Schema Registry")
            self.http.options['verify'] = self.config['schema_registry_tls_ca_cert']
        else:
            self.http.options['verify'] = True

        # Configure client certificate authentication if provided
        if self.config.get('schema_registry_tls_cert') and self.config.get('schema_registry_tls_key'):
            self.log.debug("Configuring Schema Registry with client certificate authentication")
            self.http.options['cert'] = (
                self.config['schema_registry_tls_cert'],
                self.config['schema_registry_tls_key'],
            )
        elif self.config.get('schema_registry_tls_cert'):
            # If only cert is provided without key
            self.http.options['cert'] = self.config['schema_registry_tls_cert']

    def get_subjects(self) -> list[str]:
        """Fetch all subjects from the Schema Registry.

        Returns:
            List of subject names
        """
        base_url = self.config.get('schema_registry_url')
        if not base_url:
            raise ValueError("schema_registry_url is required")

        response = self.http.get(f"{base_url}/subjects")
        response.raise_for_status()
        return response.json()

    def get_versions(self, subject: str) -> list[int]:
        """Fetch all versions for a given subject.

        Args:
            subject: Subject name

        Returns:
            List of version numbers
        """
        base_url = self.config.get('schema_registry_url')
        response = self.http.get(f"{base_url}/subjects/{subject}/versions")
        response.raise_for_status()
        return response.json()

    def get_latest_version(self, subject: str) -> dict:
        """Fetch the latest version details for a given subject.

        Args:
            subject: Subject name

        Returns:
            Dict with schema details (id, version, schema, etc.)
        """
        base_url = self.config.get('schema_registry_url')
        response = self.http.get(f"{base_url}/subjects/{subject}/versions/latest")
        response.raise_for_status()
        return response.json()

    def get_schema_by_id(self, schema_id: int) -> dict:
        """Fetch a schema by its ID.

        Args:
            schema_id: Schema ID

        Returns:
            Dict with schema details
        """
        base_url = self.config.get('schema_registry_url')
        response = self.http.get(f"{base_url}/schemas/ids/{schema_id}")
        response.raise_for_status()
        return response.json()
