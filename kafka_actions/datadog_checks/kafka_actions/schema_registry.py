# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Schema Registry client for schema evolution operations."""

from urllib.parse import quote


class SchemaRegistryClient:
    """Client for interacting with Confluent Schema Registry."""

    def __init__(self, base_url: str, http, log):
        """Initialize Schema Registry client.

        Args:
            base_url: Schema Registry base URL
            http: HTTP client instance
            log: Logger instance
        """
        self.base_url = base_url.rstrip('/')
        self.http = http
        self.log = log

    def register_schema(
        self,
        subject: str,
        schema: str,
        schema_type: str = 'AVRO',
        references: list[dict[str, any]] | None = None,
    ) -> dict[str, any]:
        """Register a new schema version.

        Args:
            subject: Schema subject name
            schema: Schema definition (JSON string)
            schema_type: Schema type (AVRO, JSON, PROTOBUF)
            references: List of schema references

        Returns:
            Dict with 'id' of registered schema
        """
        payload = {
            'schema': schema,
            'schemaType': schema_type,
        }

        if references:
            payload['references'] = references

        url = f"{self.base_url}/subjects/{quote(subject, safe='')}/versions"

        try:
            response = self.http.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            self.log.info("Schema registered for subject '%s' with ID %d", subject, result['id'])
            return result
        except Exception as e:
            self.log.error("Failed to register schema for subject '%s': %s", subject, e)
            raise

    def check_compatibility(
        self,
        subject: str,
        schema: str,
        version: str = 'latest',
    ) -> dict[str, bool]:
        """Check if a schema is compatible with a subject version.

        Args:
            subject: Schema subject name
            schema: Schema to check
            version: Version to check against (default 'latest')

        Returns:
            Dict with 'is_compatible' boolean
        """
        payload = {'schema': schema}
        url = f"{self.base_url}/compatibility/subjects/{quote(subject, safe='')}/versions/{version}"

        try:
            response = self.http.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            self.log.debug("Compatibility check for '%s': %s", subject, result.get('is_compatible'))
            return result
        except Exception as e:
            self.log.error("Failed to check compatibility for subject '%s': %s", subject, e)
            raise

    def get_schema_by_id(self, schema_id: int) -> dict[str, any]:
        """Get schema by ID.

        Args:
            schema_id: Global schema ID

        Returns:
            Dict with schema details
        """
        url = f"{self.base_url}/schemas/ids/{schema_id}"

        try:
            response = self.http.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log.error("Failed to get schema ID %d: %s", schema_id, e)
            raise

    def get_latest_schema(self, subject: str) -> dict[str, any]:
        """Get latest schema version for a subject.

        Args:
            subject: Schema subject name

        Returns:
            Dict with schema details
        """
        url = f"{self.base_url}/subjects/{quote(subject, safe='')}/versions/latest"

        try:
            response = self.http.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log.error("Failed to get latest schema for subject '%s': %s", subject, e)
            raise

    def delete_schema(self, subject: str, version: str | None = None) -> list[int]:
        """Delete schema version(s) for a subject.

        Args:
            subject: Schema subject name
            version: Specific version to delete (None to delete all)

        Returns:
            List of deleted version numbers
        """
        if version:
            url = f"{self.base_url}/subjects/{quote(subject, safe='')}/versions/{version}"
        else:
            url = f"{self.base_url}/subjects/{quote(subject, safe='')}"

        try:
            response = self.http.delete(url)
            response.raise_for_status()
            result = response.json()
            self.log.info("Deleted schema version(s) for subject '%s'", subject)
            return result if isinstance(result, list) else [result]
        except Exception as e:
            self.log.error("Failed to delete schema for subject '%s': %s", subject, e)
            raise
