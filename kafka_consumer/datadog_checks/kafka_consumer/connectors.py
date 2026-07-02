# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

from datadog_checks.kafka_consumer.cache import CacheHelper

if TYPE_CHECKING:
    from datadog_checks.kafka_consumer.config import KafkaConfig

SENSITIVE_KEY_PATTERN = re.compile(
    r'(?i)(password|secret|\.key$|_key$|sasl\.jaas\.config|api\.key|api\.secret'
    r'|\btoken\b|passphrase|keyfile|connection\.url|basic\.auth\.user\.info|private\.key)'
)


def _build_http_kwargs(
    username: str | None,
    password: str | None,
    tls_verify: bool,
    tls_ca_cert: str | None,
    tls_cert: str | None,
    tls_key: str | None,
) -> dict[str, Any]:
    """Build auth and TLS kwargs for a requests-compatible HTTP client."""
    kwargs: dict[str, Any] = {}
    if username and password:
        kwargs['auth'] = (username, password)
    if not tls_verify:
        kwargs['verify'] = False
    elif tls_ca_cert:
        kwargs['verify'] = tls_ca_cert
    else:
        kwargs['verify'] = True
    if tls_cert and tls_key:
        kwargs['cert'] = (tls_cert, tls_key)
    elif tls_cert:
        kwargs['cert'] = tls_cert
    return kwargs


CONNECTOR_CONFIG_CACHE_KEY = 'kafka_connector_config_cache'
CONNECTOR_PLUGINS_CACHE_KEY = 'kafka_connector_plugins_cache'
CONNECTOR_PLUGINS_EVENT_CACHE_KEY = 'kafka_connector_plugins_event_cache'
CONNECTOR_CONFIG_CACHE_MAX_SIZE = 5_000


def _short_class_name(full_class: str) -> str:
    """Return the rightmost component of a fully-qualified Java class name."""
    return full_class.rsplit('.', 1)[-1] if full_class else full_class


class KafkaConnectCollector:
    """Collects Kafka Connect connector metrics and config events."""

    def __init__(self, check, config: 'KafkaConfig', log: logging.Logger) -> None:
        self.check = check
        self.config = config
        self.log = log
        self.http = check.http

        self.cache = CacheHelper(check, log, config._kafka_configs_refresh_interval)

        self._oauth_token: str | None = None
        self._oauth_token_expiry: float = 0.0
        self._http_kwargs: dict[str, Any] = {}
        self._configure_http()

    def _configure_http(self) -> None:
        """Build per-request HTTP kwargs for Kafka Connect auth and TLS."""
        self._http_kwargs = _build_http_kwargs(
            self.config._kafka_connect_username,
            self.config._kafka_connect_password,
            self.config._kafka_connect_tls_verify,
            self.config._kafka_connect_tls_ca_cert,
            self.config._kafka_connect_tls_cert,
            self.config._kafka_connect_tls_key,
        )

    def _get_request_kwargs(self) -> dict[str, Any]:
        """Return per-request kwargs including the current OAuth bearer token if set."""
        kwargs: dict[str, Any] = dict(self._http_kwargs)
        if self._oauth_token:
            extra_headers: dict[str, str] = {'Authorization': f'Bearer {self._oauth_token}'}
            oauth_config = self.config._kafka_connect_oauth_token_provider
            if oauth_config:
                custom_headers = oauth_config.get('custom_headers')
                if custom_headers:
                    extra_headers.update(custom_headers)
            kwargs['extra_headers'] = extra_headers
        return kwargs

    def _fetch_oidc_token(self, oauth_config: dict[str, Any]) -> tuple[str, float]:
        """Fetch an OIDC token using client credentials grant."""
        token_url = oauth_config['url']
        client_id = oauth_config['client_id']
        client_secret = oauth_config['client_secret']

        data: dict[str, Any] = {'grant_type': 'client_credentials'}
        scope = oauth_config.get('scope')
        if scope:
            data['scope'] = scope

        options: dict[str, Any] = {'auth': (client_id, client_secret), 'timeout': self.config._request_timeout}
        tls_ca_cert = oauth_config.get('tls_ca_cert')
        if tls_ca_cert:
            options['verify'] = tls_ca_cert

        response = self.http.post(token_url, data=data, **options)
        response.raise_for_status()
        token_data = response.json()

        access_token = token_data['access_token']
        expires_in = token_data.get('expires_in', 300)
        expires_at = time.time() + expires_in

        return access_token, expires_at

    def _refresh_oauth_token(self) -> None:
        oauth_config = self.config._kafka_connect_oauth_token_provider
        if not oauth_config:
            return

        if self._oauth_token and time.time() < (self._oauth_token_expiry - 30):
            return

        token, expires_at = self._fetch_oidc_token(oauth_config)
        self._oauth_token = token
        self._oauth_token_expiry = expires_at
        self.log.debug("Kafka Connect OAuth token refreshed, expires at %s", expires_at)

    def collect(self, cluster_id: str) -> dict[str, bool]:
        """Collect connector data and return connectivity status per endpoint.

        Returns a mapping of endpoint URL to connection success (True/False).
        """
        if self.config._kafka_connect_oauth_token_provider:
            try:
                self._refresh_oauth_token()
            except Exception as e:
                if self._oauth_token and time.time() < self._oauth_token_expiry:
                    self.log.warning("OAuth refresh failed, proceeding with existing token: %s", e)
                else:
                    self.log.error("Failed to refresh Kafka Connect OAuth token: %s", e)
                    return dict.fromkeys(self.config._kafka_connect_urls, False)

        connectivity: dict[str, bool] = {}

        for url in self.config._kafka_connect_urls:
            try:
                self._collect_rest(url, cluster_id)
                connectivity[url] = True
            except Exception as e:
                self.log.error("Error collecting Kafka Connect data from %s: %s (%s)", url, e, type(e).__name__)
                connectivity[url] = False

        return connectivity

    def _collect_rest(self, url: str, cluster_id: str) -> None:
        endpoint = f'{url.rstrip("/")}/connectors'

        def _fetch(expand: str | list[str]) -> Any:
            response = self.http.get(
                endpoint,
                params={'expand': expand},
                timeout=self.config._request_timeout,
                **self._get_request_kwargs(),
            )
            response.raise_for_status()
            return response.json()

        connectors_data = _fetch(['info', 'status'])

        if not isinstance(connectors_data, dict):
            # A combined expand list is serialized as repeated query params (expand=info&expand=status),
            # which Confluent Cloud's expansions endpoint doesn't honor — it returns the unexpanded
            # connector-name list instead. Retry with a single expand value before concluding the
            # worker predates Kafka 2.3 / CP 5.3 and doesn't support expand at all.
            connectors_data = _fetch('info')

        if not isinstance(connectors_data, dict):
            self.log.warning(
                "Unexpected response shape from %s/connectors (got %s, expected dict). "
                "The Connect worker may not support the expand parameter — Kafka 2.3+ / CP 5.3+ is required.",
                url,
                type(connectors_data).__name__,
            )
            return

        # Confluent Cloud honors only one expand value per request; fetch any missing section separately and merge.
        for section in ('info', 'status'):
            if any((entry or {}).get(section) is None for entry in connectors_data.values()):
                try:
                    self._merge_expand(connectors_data, _fetch(section), section)
                except Exception as e:
                    self.log.warning(
                        "Failed to fetch supplementary '%s' section from %s/connectors, emitting partial data: %s",
                        section,
                        url,
                        e,
                    )

        tags_base = self.config._get_tags(cluster_id) + [f'connect_url:{url}']
        self.check.gauge('connector.count', len(connectors_data), tags=tags_base)
        self._emit_connector_metrics(connectors_data, tags_base)
        self._emit_connector_config_events(connectors_data, cluster_id, url)
        self._collect_plugins(url, cluster_id)

    @staticmethod
    def _merge_expand(connectors_data: dict[str, Any], expanded: Any, section: str) -> None:
        if not isinstance(expanded, dict):
            return
        for name, entry in connectors_data.items():
            if entry is None:
                continue
            if entry.get(section) is None and isinstance(expanded.get(name), dict):
                val = expanded[name].get(section)
                if val is not None:
                    entry[section] = val

    def _emit_connector_metrics(self, connectors_data: dict[str, Any], tags_base: list[str]) -> None:
        for name, data in connectors_data.items():
            if data is None:
                continue
            info = data.get('info') or {}
            status = data.get('status') or {}

            connector_type = info.get('type', 'unknown')
            full_class = (info.get('config') or {}).get('connector.class', '')
            connector_class = _short_class_name(full_class)
            connector_state = (status.get('connector') or {}).get('state', 'UNKNOWN').lower()

            connector_tags = tags_base + [
                f'connector:{name}',
                f'connector_type:{connector_type}',
                f'connector_class:{connector_class}',
                f'connector_full_class:{full_class}',
                f'connector_state:{connector_state}',
            ]

            tasks = status.get('tasks') or []
            self.check.gauge('connector.task.count', len(tasks), tags=connector_tags)

            task_state_counts: dict[str, int] = {}
            for task in tasks:
                task_state = (task.get('state') or 'UNKNOWN').lower()
                task_state_counts[task_state] = task_state_counts.get(task_state, 0) + 1
                task_id = task.get('id', '')
                task_tags = connector_tags + [f'task_id:{task_id}', f'task_state:{task_state}']
                self.check.gauge(
                    'connector.task.running',
                    1 if task_state == 'running' else 0,
                    tags=task_tags,
                )
            for state_name, count in task_state_counts.items():
                self.check.gauge('connector.tasks', count, tags=connector_tags + [f'task_state:{state_name}'])

    def _emit_connector_config_events(self, connectors_data: dict[str, Any], cluster_id: str, url: str) -> None:
        connector_contents: dict[str, str] = {}

        for name, data in connectors_data.items():
            if data is None:
                continue
            info = data.get('info') or {}
            status = data.get('status') or {}

            connector_type = info.get('type', 'unknown')
            connector_state = (status.get('connector') or {}).get('state', 'UNKNOWN')
            tasks = status.get('tasks') or []
            raw_config = info.get('config') or {}

            redacted_config = {k: '[hidden]' if SENSITIVE_KEY_PATTERN.search(k) else v for k, v in raw_config.items()}

            content = {
                'kafka_cluster_id': cluster_id,
                **self.config._original_cluster_id_field(),
                'connector': name,
                'connector_type': connector_type,
                'connector_state': connector_state,
                'task_count': len(tasks),
                'connect_url': url,
                'config_type': 'connector',
                'config': redacted_config,
            }
            connector_contents[name] = json.dumps(content, sort_keys=True)

        safe_url = quote(url, safe='')
        cache_key = f'{CONNECTOR_CONFIG_CACHE_KEY}:{safe_url}'
        connectors_to_emit = self.cache.get_events_to_send(
            cache_key, connector_contents, max_cache_size=CONNECTOR_CONFIG_CACHE_MAX_SIZE
        )

        collection_timestamp = int(time.time() * 1000)
        for name in connectors_to_emit:
            event = json.loads(connector_contents[name])
            event['collection_timestamp'] = collection_timestamp
            self.check.event_platform_event(json.dumps(event), 'data-streams-message')

    def _collect_plugins(self, url: str, cluster_id: str) -> None:
        safe_url = quote(url, safe='')
        fetch_cache_key = f'{CONNECTOR_PLUGINS_CACHE_KEY}:{safe_url}'
        items_to_fetch = self.cache.get_items_to_fetch(fetch_cache_key, ['plugins'])
        if not items_to_fetch:
            return

        response = self.http.get(
            f'{url.rstrip("/")}/connector-plugins',
            timeout=self.config._request_timeout,
            **self._get_request_kwargs(),
        )
        response.raise_for_status()
        plugins = response.json()

        self.cache.mark_items_fetched(
            fetch_cache_key,
            ['plugins'],
            ttl_base=self.cache.refresh_interval,
            ttl_jitter=self.cache.refresh_jitter,
        )

        event_cache_key = f'{CONNECTOR_PLUGINS_EVENT_CACHE_KEY}:{safe_url}'
        content_dict = {
            'kafka_cluster_id': cluster_id,
            **self.config._original_cluster_id_field(),
            'connect_url': url,
            'config_type': 'connector_plugins',
            'plugins': plugins,
        }
        content = json.dumps(content_dict, sort_keys=True)
        if self.cache.get_events_to_send(
            event_cache_key, {'plugins': content}, max_cache_size=CONNECTOR_CONFIG_CACHE_MAX_SIZE
        ):
            event = json.loads(content)
            event['collection_timestamp'] = int(time.time() * 1000)
            self.check.event_platform_event(json.dumps(event), 'data-streams-message')
