# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
from urllib.parse import quote


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
        response = self.http.get(f"{base_url}/subjects/{quote(subject, safe='')}/versions")
        response.raise_for_status()
        return response.json()

    def get_latest_version(self, subject):
        """Fetch the latest version details for a given subject."""
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/subjects/{quote(subject, safe='')}/versions/latest")
        response.raise_for_status()
        return response.json()

    def get_version(self, subject, version):
        """Fetch a specific version for a given subject.

        Args:
            subject: The subject name
            version: The version number or 'latest'

        Returns:
            dict: Schema version details including id, version, schema, schemaType, and references
        """
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/subjects/{quote(subject, safe='')}/versions/{version}")
        response.raise_for_status()
        return response.json()

    def get_schema_by_id(self, schema_id):
        """Fetch a schema by its global ID.

        Args:
            schema_id: The global schema ID

        Returns:
            dict: Schema details including schema and schemaType
        """
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/schemas/ids/{schema_id}")
        response.raise_for_status()
        return response.json()

    def get_schema_metadata(self, subject, version='latest'):
        """Extract metadata from a schema including owner and other custom properties.

        Args:
            subject: The subject name
            version: The version number or 'latest'

        Returns:
            dict: Metadata extracted from schema, or empty dict if no metadata found
        """
        try:
            version_data = self.get_version(subject, version)
            schema_str = version_data.get('schema', '')

            # Try to parse schema to extract metadata
            try:
                schema_obj = json.loads(schema_str)
                # Check for metadata field in schema
                if isinstance(schema_obj, dict):
                    # Look for metadata in various common locations
                    metadata = {}

                    # Check for top-level metadata field
                    if 'metadata' in schema_obj:
                        metadata.update(schema_obj['metadata'])

                    # Check for properties within metadata
                    if 'metadata' in schema_obj and 'properties' in schema_obj['metadata']:
                        metadata.update(schema_obj['metadata']['properties'])

                    # Check for doc field which sometimes contains metadata
                    if 'doc' in schema_obj:
                        metadata['doc'] = schema_obj['doc']

                    return metadata
            except json.JSONDecodeError:
                self.log.debug("Could not parse schema as JSON for subject %s", subject)

            return {}
        except Exception as e:
            self.log.error("Failed to fetch schema metadata for subject %s: %s", subject, e)
            return {}

    def get_global_compatibility(self):
        """Get the global compatibility level configuration.

        Returns:
            dict: Contains 'compatibilityLevel' key with values like
                  'BACKWARD', 'FORWARD', 'FULL', 'NONE', etc.
        """
        base_url = self.config._collect_schema_registry
        response = self.http.get(f"{base_url}/config")
        response.raise_for_status()
        return response.json()

    def get_subject_compatibility(self, subject):
        """Get the compatibility level for a specific subject.

        Args:
            subject: The subject name

        Returns:
            dict: Contains 'compatibilityLevel' key, or falls back to global if not set
        """
        base_url = self.config._collect_schema_registry
        try:
            response = self.http.get(f"{base_url}/config/{quote(subject, safe='')}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log.debug("Subject-specific compatibility not found for %s, falling back to global: %s", subject, e)
            return self.get_global_compatibility()

    def get_global_mode(self):
        """Get the global mode configuration.

        Returns:
            dict: Contains 'mode' key with values like 'READWRITE', 'READONLY', 'IMPORT'
        """
        base_url = self.config._collect_schema_registry
        try:
            response = self.http.get(f"{base_url}/mode")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log.debug("Failed to fetch global mode (may not be supported): %s", e)
            return {'mode': 'UNKNOWN'}

    def get_subject_mode(self, subject):
        """Get the mode for a specific subject.

        Args:
            subject: The subject name

        Returns:
            dict: Contains 'mode' key, or falls back to global if not set
        """
        base_url = self.config._collect_schema_registry
        try:
            response = self.http.get(f"{base_url}/mode/{quote(subject, safe='')}")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log.debug("Subject-specific mode not found for %s, falling back to global: %s", subject, e)
            return self.get_global_mode()

    def check_compatibility(self, subject, version, schema):
        """Check if a schema is compatible with a specific version.

        Args:
            subject: The subject name
            version: The version to check against
            schema: The schema JSON string to check

        Returns:
            dict: Contains 'is_compatible' boolean indicating compatibility
        """
        base_url = self.config._collect_schema_registry
        payload = {'schema': schema}
        try:
            response = self.http.post(
                f"{base_url}/compatibility/subjects/{quote(subject, safe='')}/versions/{version}", json=payload
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log.error("Failed to check compatibility for subject %s: %s", subject, e)
            return {'is_compatible': False, 'error': str(e)}

    def get_schema_types(self):
        """Get the list of supported schema types in this Schema Registry.

        Returns:
            list: Supported schema types like ['AVRO', 'JSON', 'PROTOBUF']
        """
        base_url = self.config._collect_schema_registry
        try:
            response = self.http.get(f"{base_url}/schemas/types")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log.debug("Failed to fetch schema types (may not be supported): %s", e)
            return ['AVRO']  # Default fallback

    def get_subjects_with_prefix(self, prefix=None, deleted=False):
        """Get subjects, optionally filtered by prefix and including deleted subjects.

        Args:
            prefix: Optional prefix to filter subjects
            deleted: Whether to include deleted subjects

        Returns:
            list: List of subject names
        """
        base_url = self.config._collect_schema_registry
        params = {}
        if prefix:
            params['subjectPrefix'] = prefix
        if deleted:
            params['deleted'] = 'true'

        try:
            response = self.http.get(f"{base_url}/subjects", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log.warning("Failed to fetch subjects with params %s: %s", params, e)
            return self.get_subjects()  # Fallback to basic method

    def get_schema_references(self, subject, version='latest'):
        """Get schema references for a specific version.

        Args:
            subject: The subject name
            version: The version number or 'latest'

        Returns:
            list: List of schema references, each containing name, subject, and version
        """
        try:
            version_data = self.get_version(subject, version)
            return version_data.get('references', [])
        except Exception as e:
            self.log.error("Failed to fetch schema references for %s: %s", subject, e)
            return []

    def get_all_subject_details(self, subject):
        """Get comprehensive details about a subject including all versions, config, and metadata.

        Args:
            subject: The subject name

        Returns:
            dict: Comprehensive subject information
        """
        details = {
            'subject': subject,
            'versions': [],
            'compatibility': None,
            'mode': None,
            'latest_version': None,
            'metadata': {},
        }

        try:
            # Get all versions
            details['versions'] = self.get_versions(subject)

            # Get latest version details
            details['latest_version'] = self.get_latest_version(subject)

            # Get compatibility config
            details['compatibility'] = self.get_subject_compatibility(subject)

            # Get mode
            details['mode'] = self.get_subject_mode(subject)

            # Get metadata
            details['metadata'] = self.get_schema_metadata(subject)

            # Get references
            details['references'] = self.get_schema_references(subject)

        except Exception as e:
            self.log.error("Failed to fetch complete details for subject %s: %s", subject, e)

        return details
