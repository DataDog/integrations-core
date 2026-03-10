# (C) Datadog, Inc. 2025-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""Schema Registry client for fetching schemas by ID."""

import time


class SchemaRegistryClient:
    """Fetches schemas from Confluent Schema Registry via HTTP."""

    def __init__(self, http, base_url: str, log, config: dict):
        self._http = http
        self._base_url = base_url.rstrip('/')
        self._log = log
        self._config = config
        self._schema_cache: dict[int, tuple[str, str]] = {}
        self._oauth_token = None
        self._oauth_token_expiry = 0.0

        self._configure_http()

    def _configure_http(self):
        """Set up auth/TLS on the HTTP client (same pattern as kafka_consumer cluster_metadata)."""
        username = self._config.get('schema_registry_username')
        password = self._config.get('schema_registry_password')
        if username and password:
            self._log.debug("Configuring Schema Registry with Basic Authentication")
            self._http.options['auth'] = (username, password)

        tls_verify = self._config.get('schema_registry_tls_verify')
        tls_ca_cert = self._config.get('schema_registry_tls_ca_cert')
        if tls_verify is False:
            self._log.debug("Schema Registry TLS verification is disabled")
            self._http.options['verify'] = False
        elif tls_ca_cert:
            self._log.debug("Using custom CA certificate for Schema Registry")
            self._http.options['verify'] = tls_ca_cert
        else:
            self._http.options['verify'] = True

        tls_cert = self._config.get('schema_registry_tls_cert')
        tls_key = self._config.get('schema_registry_tls_key')
        if tls_cert and tls_key:
            self._log.debug("Configuring Schema Registry with client certificate authentication")
            self._http.options['cert'] = (tls_cert, tls_key)
        elif tls_cert:
            self._http.options['cert'] = tls_cert

    def _refresh_oauth_token(self):
        """Fetch or refresh the OAuth token if configured and expired."""
        oauth_config = self._config.get('schema_registry_oauth_token_provider')
        if not oauth_config:
            return

        if self._oauth_token and time.time() < (self._oauth_token_expiry - 30):
            return

        token_url = oauth_config['url']
        client_id = oauth_config['client_id']
        client_secret = oauth_config['client_secret']

        data = {'grant_type': 'client_credentials'}
        scope = oauth_config.get('scope')
        if scope:
            data['scope'] = scope

        options = {}
        tls_ca_cert = oauth_config.get('tls_ca_cert')
        if tls_ca_cert:
            options['verify'] = tls_ca_cert

        response = self._http.post(token_url, data=data, auth=(client_id, client_secret), **options)
        response.raise_for_status()
        token_data = response.json()

        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 300)

        self._oauth_token = access_token
        self._oauth_token_expiry = time.time() + expires_in

        headers = {**self._http.options.get('headers', {}), 'Authorization': f'Bearer {access_token}'}
        custom_headers = oauth_config.get('custom_headers')
        if custom_headers:
            headers.update(custom_headers)
        self._http.options['headers'] = headers

        self._log.debug("Schema Registry OAuth token refreshed, expires at %s", self._oauth_token_expiry)

    def get_schema(self, schema_id: int) -> tuple[str, str]:
        """Fetch schema by ID from the registry. Returns (schema_string, schema_type).

        For PROTOBUF schemas, requests format=serialized to get a base64-encoded
        FileDescriptorProto that can be parsed directly by the protobuf library.
        For AVRO/JSON schemas, returns the raw schema string.

        Schemas are immutable in the registry, so results are cached forever.
        """
        cached = self._schema_cache.get(schema_id)
        if cached is not None:
            return cached

        self._refresh_oauth_token()

        url = f"{self._base_url}/schemas/ids/{schema_id}"
        self._log.debug("Fetching schema ID %d from %s", schema_id, url)

        response = self._http.get(url)
        response.raise_for_status()
        data = response.json()

        schema_str = data['schema']
        schema_type = data.get('schemaType', 'AVRO')

        # For protobuf, re-fetch with format=serialized to get a base64-encoded
        # FileDescriptorProto instead of raw .proto text.
        if schema_type == 'PROTOBUF':
            serialized_url = f"{url}?format=serialized"
            self._log.debug("Fetching protobuf schema %d in serialized format", schema_id)
            serialized_response = self._http.get(serialized_url)
            serialized_response.raise_for_status()
            schema_str = serialized_response.json()['schema']

        result = (schema_str, schema_type)
        self._schema_cache[schema_id] = result
        return result
