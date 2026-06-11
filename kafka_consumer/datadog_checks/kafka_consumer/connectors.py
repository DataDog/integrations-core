# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any
from urllib.parse import quote

import requests

from datadog_checks.kafka_consumer.event_cache_mixin import EventCacheMixin

if TYPE_CHECKING:
    from datadog_checks.kafka_consumer.config import KafkaConfig

SENSITIVE_KEY_PATTERN = re.compile(r'(?i)(password|secret|\.key$|sasl\.jaas\.config|api\.key|api\.secret)')

CONNECTOR_CONFIG_CACHE_KEY = 'kafka_connector_config_cache'
CONNECTOR_PLUGINS_CACHE_KEY = 'kafka_connector_plugins_cache'
CONNECTOR_PLUGINS_EVENT_CACHE_KEY = 'kafka_connector_plugins_event_cache'
CONNECTOR_CONFIG_CACHE_MAX_SIZE = 5_000

IMPORTANT_CONNECTOR_CONFIG_KEYS = [
    'connector.class',
    'tasks.max',
    'topics',
    'topics.regex',
    'topic.prefix',
    'key.converter',
    'value.converter',
    'key.converter.schema.registry.url',
    'value.converter.schema.registry.url',
    'header.converter',
    'errors.tolerance',
    'errors.retry.delay.max.ms',
    'errors.retry.timeout',
    'errors.deadletterqueue.topic.name',
    'errors.deadletterqueue.context.headers.enable',
    'transforms',
    'predicates',
    'source.cluster.alias',
    'target.cluster.alias',
    'source.cluster.bootstrap.servers',
    'target.cluster.bootstrap.servers',
    'replication.factor',
    'connection.url',
    'connection.host',
    'connection.port',
    'database.hostname',
    'database.port',
    'database.dbname',
    'database.server.name',
    'aws.region',
    's3.bucket.name',
    'topic.creation.default.replication.factor',
    'topic.creation.default.partitions',
]


def _short_class_name(full_class: str) -> str:
    """Return the rightmost component of a fully-qualified Java class name."""
    return full_class.rsplit('.', 1)[-1] if full_class else full_class


def _fetch_oidc_token(oauth_config: dict, session: requests.Session, timeout: float) -> tuple[str, float]:
    """Fetch an OIDC token using client credentials grant."""
    token_url = oauth_config['url']
    client_id = oauth_config['client_id']
    client_secret = oauth_config['client_secret']

    data: dict = {'grant_type': 'client_credentials'}
    scope = oauth_config.get('scope')
    if scope:
        data['scope'] = scope

    kwargs: dict = {'auth': (client_id, client_secret), 'timeout': timeout}
    tls_ca_cert = oauth_config.get('tls_ca_cert')
    if tls_ca_cert:
        kwargs['verify'] = tls_ca_cert

    response = session.post(token_url, data=data, **kwargs)
    response.raise_for_status()
    token_data = response.json()

    access_token = token_data['access_token']
    expires_in = token_data.get('expires_in', 300)
    expires_at = time.time() + expires_in

    return access_token, expires_at


class KafkaConnectCollector(EventCacheMixin):
    """Collects Kafka Connect connector metrics and config events."""

    def __init__(self, check, config: 'KafkaConfig', log: logging.Logger) -> None:
        self.check = check
        self.config = config
        self.log = log

        configs_refresh = self.config._kafka_configs_refresh_interval
        self._configs_refresh_interval = configs_refresh
        self._configs_refresh_jitter = max(15, configs_refresh // 10)

        self._session: requests.Session | None = None
        self._oauth_token: str | None = None
        self._oauth_token_expiry: float = 0

    def _get_session(self) -> requests.Session:
        if self._session is None:
            self._session = requests.Session()
            self._configure_session(self._session)
        return self._session

    def _configure_session(self, session: requests.Session) -> None:
        if self.config._kafka_connect_username and self.config._kafka_connect_password:
            session.auth = (self.config._kafka_connect_username, self.config._kafka_connect_password)

        if not self.config._kafka_connect_tls_verify:
            session.verify = False
        elif self.config._kafka_connect_tls_ca_cert:
            session.verify = self.config._kafka_connect_tls_ca_cert
        else:
            session.verify = True

        if self.config._kafka_connect_tls_cert and self.config._kafka_connect_tls_key:
            session.cert = (self.config._kafka_connect_tls_cert, self.config._kafka_connect_tls_key)
        elif self.config._kafka_connect_tls_cert:
            session.cert = self.config._kafka_connect_tls_cert

    def _refresh_oauth_token(self) -> None:
        oauth_config = self.config._kafka_connect_oauth_token_provider
        if not oauth_config:
            return

        if self._oauth_token and time.time() < (self._oauth_token_expiry - 30):
            return

        session = self._get_session()
        timeout = self.config._request_timeout
        token, expires_at = _fetch_oidc_token(oauth_config, session, timeout)

        self._oauth_token = token
        self._oauth_token_expiry = expires_at
        session.headers['Authorization'] = f'Bearer {token}'

        custom_headers = oauth_config.get('custom_headers')
        if custom_headers:
            session.headers.update(custom_headers)

        self.log.debug("Kafka Connect OAuth token refreshed, expires at %s", expires_at)

    def collect(self, cluster_id: str) -> dict[str, bool]:
        """Collect connector data and return connectivity status per endpoint.

        Returns a mapping of endpoint identifier to connection success (True/False).
        REST URL endpoints use the URL as key; Confluent Cloud uses 'confluent_cloud:<env>:<cluster>'.
        """
        if self.config._kafka_connect_oauth_token_provider:
            try:
                self._refresh_oauth_token()
            except Exception as e:
                self.log.error("Failed to refresh Kafka Connect OAuth token: %s", e)
                failed: dict[str, bool] = dict.fromkeys(self.config._kafka_connect_urls, False)
                if (
                    self.config._kafka_connect_confluent_cloud_environment_id
                    and self.config._kafka_connect_confluent_cloud_cluster_id
                ):
                    env_id = self.config._kafka_connect_confluent_cloud_environment_id
                    cc_id = self.config._kafka_connect_confluent_cloud_cluster_id
                    failed[f'confluent_cloud:{env_id}:{cc_id}'] = False
                return failed

        connectivity: dict[str, bool] = {}

        for url in self.config._kafka_connect_urls:
            try:
                self._collect_rest(url, cluster_id)
                connectivity[url] = True
            except Exception as e:
                self.log.error("Error collecting Kafka Connect data from %s: %s (%s)", url, e, type(e).__name__)
                connectivity[url] = False

        if (
            self.config._kafka_connect_confluent_cloud_environment_id
            and self.config._kafka_connect_confluent_cloud_cluster_id
        ):
            env_id = self.config._kafka_connect_confluent_cloud_environment_id
            cluster_id_cc = self.config._kafka_connect_confluent_cloud_cluster_id
            cc_key = f'confluent_cloud:{env_id}:{cluster_id_cc}'
            try:
                self._collect_confluent_cloud(cluster_id)
                connectivity[cc_key] = True
            except Exception as e:
                self.log.error(
                    "Error collecting Confluent Cloud Connect data for %s/%s: %s (%s)",
                    env_id,
                    cluster_id_cc,
                    e,
                    type(e).__name__,
                )
                connectivity[cc_key] = False

        return connectivity

    def _collect_rest(self, url: str, cluster_id: str) -> None:
        session = self._get_session()
        timeout = self.config._request_timeout
        response = session.get(
            f'{url.rstrip("/")}/connectors',
            params={'expand': ['info', 'status']},
            timeout=timeout,
        )
        response.raise_for_status()
        connectors_data = response.json()

        if not isinstance(connectors_data, dict):
            # Older Connect workers (pre-Kafka 2.3 / CP 5.3) ignore the expand parameter
            # and return a plain list of connector names instead of the expanded dict.
            self.log.warning(
                "Unexpected response shape from %s/connectors (got %s, expected dict). "
                "The Connect worker may not support the expand parameter — Kafka 2.3+ / CP 5.3+ is required.",
                url,
                type(connectors_data).__name__,
            )
            return

        tags_base = self._get_tags(cluster_id) + [f'connect_url:{url}']
        self.check.gauge('connector.count', len(connectors_data), tags=tags_base)

        self._emit_connector_metrics(connectors_data, tags_base)
        self._emit_connector_config_events(connectors_data, cluster_id, url)
        self._collect_plugins(url, cluster_id)

    def _emit_connector_metrics(self, connectors_data: dict[str, Any], tags_base: list[str]) -> None:
        for name, data in connectors_data.items():
            info = data.get('info', {})
            status = data.get('status', {})

            connector_type = info.get('type', 'unknown')
            full_class = (info.get('config') or {}).get('connector.class', '')
            connector_class = _short_class_name(full_class)
            connector_state = (status.get('connector') or {}).get('state', 'UNKNOWN')

            connector_tags = tags_base + [
                f'connector:{name}',
                f'connector_type:{connector_type}',
                f'connector_class:{connector_class}',
                f'connector_state:{connector_state}',
            ]
            self.check.gauge(
                'connector.running',
                1 if connector_state == 'RUNNING' else 0,
                tags=connector_tags,
            )

            tasks = status.get('tasks') or []
            count_tags = tags_base + [
                f'connector:{name}',
                f'connector_type:{connector_type}',
            ]
            self.check.gauge('connector.task.count', len(tasks), tags=count_tags)

            task_state_counts: dict[str, int] = {}
            for task in tasks:
                state = (task.get('state') or 'UNKNOWN').lower()
                task_state_counts[state] = task_state_counts.get(state, 0) + 1
            for state_name, count in task_state_counts.items():
                self.check.gauge('connector.tasks', count, tags=count_tags + [f'task_state:{state_name}'])

            if self.config._kafka_connect_collect_task_metrics:
                for task in tasks:
                    task_id = task.get('id', '')
                    task_state = (task.get('state') or 'UNKNOWN').lower()
                    task_tags = connector_tags + [f'task_id:{task_id}', f'task_state:{task_state}']
                    self.check.gauge(
                        'connector.task.running',
                        1 if task_state == 'running' else 0,
                        tags=task_tags,
                    )

    def _emit_connector_config_events(self, connectors_data: dict[str, Any], cluster_id: str, url: str) -> None:
        connector_contents: dict[str, str] = {}

        for name, data in connectors_data.items():
            info = data.get('info', {})
            status = data.get('status', {})

            connector_type = info.get('type', 'unknown')
            connector_state = (status.get('connector') or {}).get('state', 'UNKNOWN')
            tasks = status.get('tasks') or []
            raw_config = info.get('config') or {}

            truncated_config = self._truncate_connector_config(raw_config)

            # Exclude collection_timestamp from hashed content so the hash is stable
            # across cycles and dedup actually fires on unchanged configs.
            content = {
                'kafka_cluster_id': cluster_id,
                **self._original_cluster_id_field(),
                'connector': name,
                'connector_type': connector_type,
                'connector_state': connector_state,
                'task_count': len(tasks),
                'connect_url': url,
                'config_type': 'connector',
                'config': truncated_config,
            }
            connector_contents[name] = json.dumps(content, sort_keys=True)

        safe_url = quote(url, safe='')
        cache_key = f'{CONNECTOR_CONFIG_CACHE_KEY}:{safe_url}'
        connectors_to_emit = self._get_events_to_send(
            cache_key, connector_contents, max_cache_size=CONNECTOR_CONFIG_CACHE_MAX_SIZE
        )

        collection_timestamp = int(time.time() * 1000)
        for name in connectors_to_emit:
            event = json.loads(connector_contents[name])
            event['collection_timestamp'] = collection_timestamp
            self.check.event_platform_event(json.dumps(event), 'data-streams-message')

    def _truncate_connector_config(self, config: dict) -> dict:
        important: dict[str, str] = {}
        rest: dict[str, str] = {}

        for key, value in config.items():
            if key in IMPORTANT_CONNECTOR_CONFIG_KEYS:
                important[key] = value
            else:
                rest[key] = value

        selected = [(k, important[k]) for k in IMPORTANT_CONNECTOR_CONFIG_KEYS if k in important]
        remaining_slots = 30 - len(selected)
        for key in sorted(rest.keys()):
            if remaining_slots <= 0:
                break
            selected.append((key, rest[key]))
            remaining_slots -= 1

        return {k: '[hidden]' if SENSITIVE_KEY_PATTERN.search(k) else v for k, v in selected}

    def _collect_plugins(self, url: str, cluster_id: str) -> None:
        safe_url = quote(url, safe='')
        fetch_cache_key = f'{CONNECTOR_PLUGINS_CACHE_KEY}:{safe_url}'
        items_to_fetch = self._get_items_to_fetch(fetch_cache_key, ['plugins'])
        if not items_to_fetch:
            return

        session = self._get_session()
        timeout = self.config._request_timeout
        response = session.get(f'{url.rstrip("/")}/connector-plugins', timeout=timeout)
        response.raise_for_status()
        plugins = response.json()

        self._mark_items_fetched(
            fetch_cache_key,
            ['plugins'],
            ttl_base=self._configs_refresh_interval,
            ttl_jitter=self._configs_refresh_jitter,
        )

        event_cache_key = f'{CONNECTOR_PLUGINS_EVENT_CACHE_KEY}:{safe_url}'
        # Exclude collection_timestamp from hashed content so dedup fires on unchanged plugin lists.
        content_dict = {
            'kafka_cluster_id': cluster_id,
            **self._original_cluster_id_field(),
            'connect_url': url,
            'config_type': 'connector_plugins',
            'plugins': plugins,
        }
        content = json.dumps(content_dict, sort_keys=True)
        if self._get_events_to_send(
            event_cache_key, {'plugins': content}, max_cache_size=CONNECTOR_CONFIG_CACHE_MAX_SIZE
        ):
            event = json.loads(content)
            event['collection_timestamp'] = int(time.time() * 1000)
            self.check.event_platform_event(json.dumps(event), 'data-streams-message')

    def _collect_confluent_cloud(self, cluster_id: str) -> None:
        env_id = self.config._kafka_connect_confluent_cloud_environment_id
        cc_cluster_id = self.config._kafka_connect_confluent_cloud_cluster_id
        base = self.config._kafka_connect_confluent_cloud_url.rstrip('/')
        url = f'{base}/connect/v1/environments/{env_id}/clusters/{cc_cluster_id}'
        self._collect_rest(url, cluster_id)

