# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os
import time
from collections.abc import Callable
from typing import Any
from urllib.parse import quote

import mock
import pytest
from confluent_kafka.admin import AdminClient
from confluent_kafka.cimpl import NewTopic

from datadog_checks.dev import EnvVars, TempDir, WaitFor, docker_run
from datadog_checks.dev._env import e2e_testing, get_state, save_state
from datadog_checks.dev.ci import running_on_ci
from datadog_checks.kafka_consumer import KafkaCheck
from datadog_checks.kafka_consumer.client import KafkaClient

from . import common
from .common import get_cluster_id
from .runners import Consumer, Producer

KERBEROS_SECRET_DIR_STATE = 'kafka_consumer_kerberos_secret_dir'
KRB5_CONFIG = (
    f"{common.HERE}/docker/kerberos/kdc/krb5_agent.conf"
    if running_on_ci()
    else f"{common.HERE}/docker/kerberos/kdc/krb5_local.conf"
)


def seed_mock_kafka_client():
    """Minimal Kafka client mock sufficient for the connector-focused tests."""
    client = mock.create_autospec(KafkaClient)
    client.get_cluster_id.return_value = 'cluster-1'
    client.list_consumer_groups.return_value = []
    client.list_consumer_group_offsets.return_value = []
    client._cluster_metadata = None
    return client


SAMPLE_CONNECTORS_RESPONSE = {
    'demo-source': {
        'info': {
            'type': 'source',
            'config': {
                'connector.class': 'org.apache.kafka.connect.mirror.MirrorSourceConnector',
                'tasks.max': '2',
                'topics': 'demo-orders',
            },
        },
        'status': {
            'connector': {'state': 'RUNNING'},
            'tasks': [
                {'id': 0, 'state': 'RUNNING', 'worker_id': 'connect:8083'},
                {'id': 1, 'state': 'RUNNING', 'worker_id': 'connect:8083'},
            ],
        },
    },
    'demo-heartbeat': {
        'info': {
            'type': 'source',
            'config': {'connector.class': 'org.apache.kafka.connect.mirror.MirrorHeartbeatConnector'},
        },
        'status': {
            'connector': {'state': 'PAUSED'},
            'tasks': [{'id': 0, 'state': 'PAUSED', 'worker_id': 'connect:8083'}],
        },
    },
}


def connectors_url(connect_url: str) -> str:
    return f'{connect_url.rstrip("/")}/connectors'


def plugins_url(connect_url: str) -> str:
    return f'{connect_url.rstrip("/")}/connector-plugins'


def topics_url(connect_url: str, connector: str) -> str:
    return f'{connectors_url(connect_url)}/{quote(connector, safe="")}/topics'


@pytest.fixture
def run_connect_check(check, kafka_instance, dd_run_check, datadog_agent, fake_http, fake_http_response):
    """Run full KafkaCheck cycles with Kafka Connect monitoring enabled, served by `fake_http`.

    On every configured Connect URL, serves `connectors_response` (or the entry of `connectors_per_run` for
    each run), the plugin list and each connector's topics, plus the OAuth token when a token provider is
    configured. `register_overrides(respond, fail)` then runs, so a test can replace any of these: the latest
    registration for a request wins. `respond(url, **kwargs)` takes the `fake_http_response` arguments and
    `fail(url, error, method='GET')` makes the request raise `error`.

    The check catches errors around each Connect request, so a request to an unregistered URL would fail
    silently. The harness fails the test instead.

    Returns the check; requests are recorded in `fake_http.requests`. Depends on `datadog_agent` so the
    persistent cache is reset between tests.
    """

    def _run(
        connectors_response: Any = None,
        connectors_per_run: list[Any] | None = None,
        plugins_response: list[dict[str, Any]] | None = None,
        topics_response: dict[str, list[str]] | None = None,
        instance_extra: dict[str, Any] | None = None,
        oauth_token_response: dict[str, Any] | None = None,
        register_overrides: Callable[[Callable[..., Any], Callable[..., None]], None] | None = None,
        runs: int = 1,
    ) -> KafkaCheck:
        kafka_instance['kafka_connect_url'] = common.CONNECT_URL
        kafka_instance['enable_kafka_console'] = True
        if instance_extra:
            kafka_instance.update(instance_extra)

        connect_urls = kafka_instance['kafka_connect_url']
        if isinstance(connect_urls, str):
            connect_urls = [connect_urls]
        responses = connectors_per_run if connectors_per_run is not None else [connectors_response]
        connector_names = set(topics_response or {})
        for response in responses:
            if isinstance(response, dict):
                connector_names.update(response)

        registered_urls: set[str] = set()

        # Every registration repeats: the topics fetch runs in worker threads, and FakeHTTPClient is only
        # safe for concurrent requests when no registration uses `once=True`.
        def respond(url: str, **kwargs: Any) -> Any:
            registered_urls.add(url)
            return fake_http_response(url, **kwargs)

        def fail(url: str, error: Exception, method: str = 'GET') -> None:
            registered_urls.add(url)
            fake_http.register_response(method, url, error)

        for url in connect_urls:
            respond(plugins_url(url), json_data=plugins_response or [])
            for name in connector_names:
                respond(topics_url(url, name), json_data={name: {'topics': (topics_response or {}).get(name, [])}})

        oauth_provider = kafka_instance.get('kafka_connect_oauth_token_provider')
        if oauth_token_response is not None:
            respond(oauth_provider['url'], method='POST', json_data=oauth_token_response)

        if register_overrides is not None:
            register_overrides(respond, fail)

        kafka_consumer_check = check(kafka_instance)
        kafka_consumer_check.client = seed_mock_kafka_client()

        with mock.patch.object(kafka_consumer_check.metadata_collector, 'collect_all_metadata'):
            for run in range(runs):
                current = responses[min(run, len(responses) - 1)]
                if current is not None:
                    for url in connect_urls:
                        respond(connectors_url(url), json_data=current)
                dd_run_check(kafka_consumer_check)

        unregistered = sorted({request.url for request in fake_http.requests} - registered_urls)
        assert not unregistered, f'Requests sent to URLs without a registered response: {unregistered}'

        return kafka_consumer_check

    return _run


@pytest.fixture(scope='session')
def dd_environment():
    """
    Start a kafka cluster and wait for it to be up and running.
    """
    with TempDir() as secret_dir:
        os.chmod(secret_dir, 0o777)
        conditions = []

        if common.AUTHENTICATION == "kerberos":
            common.INSTANCE["sasl_kerberos_keytab"] = common.INSTANCE["sasl_kerberos_keytab"].format(secret_dir)
            save_state(KERBEROS_SECRET_DIR_STATE, secret_dir)
            conditions.append(WaitFor(wait_for_cp_kafka_topics, attempts=10, wait=10))
            common.E2E_METADATA["docker_volumes"].append(f"{secret_dir}:/var/lib/secret")

        if common.AUTHENTICATION == "ssl":
            conditions.append(WaitFor(wait_for_ssl_ready, attempts=30, wait=5))

        conditions.extend(
            [
                WaitFor(create_topics, attempts=60, wait=3),
                WaitFor(initialize_topics),
                WaitFor(is_cluster_id_available),
            ]
        )

        with docker_run(
            common.DOCKER_IMAGE_PATH,
            conditions=conditions,
            env_vars={"KRB5_CONFIG": KRB5_CONFIG, "SECRET_DIR": secret_dir},
            build=True,
        ):
            yield (
                {
                    'instances': [common.E2E_INSTANCE],
                    'init_config': {'kafka_timeout': 30},
                },
                common.E2E_METADATA,
            )


@pytest.fixture(scope='session', autouse=True)
def e2e_kerberos_client():
    """Give host-side Kerberos clients the credentials `dd_environment` set up when the environment started.

    `dd_environment` runs in the `ddev env start` process. In the `ddev env test` process the plugin turns it into a
    no-op, so its changes to `common.INSTANCE` and `KRB5_CONFIG` are missing there and `get_cluster_id` would
    authenticate with an unformatted keytab path and the runner's default Kerberos realm.
    """
    if common.AUTHENTICATION != "kerberos" or not e2e_testing():
        yield
        return

    secret_dir = get_state(KERBEROS_SECRET_DIR_STATE)
    common.INSTANCE["sasl_kerberos_keytab"] = common.INSTANCE["sasl_kerberos_keytab"].format(secret_dir)
    with EnvVars({"KRB5_CONFIG": KRB5_CONFIG}):
        yield


def is_cluster_id_available():
    return get_cluster_id() is not None


@pytest.fixture
def check():
    return lambda instance, init_config=None: KafkaCheck('kafka_consumer', init_config or {}, [instance])


@pytest.fixture
def kafka_instance():
    return copy.deepcopy(common.E2E_INSTANCE if e2e_testing() else common.INSTANCE)


def create_topics():
    client = _create_admin_client()
    response = client.list_topics(timeout=1)

    if set(common.TOPICS).issubset(set(response.topics.keys())):
        return True

    for topic in common.TOPICS:
        client.create_topics([NewTopic(topic, 2, 1)])
        time.sleep(1)

    # Make sure the topics in `TOPICS` are created. Brokers may have more topics (such as internal topics)
    # so we only check if it contains the topic we need.
    return set(common.TOPICS).issubset(set(client.list_topics(timeout=1).topics.keys()))


def wait_for_cp_kafka_topics():
    client = _create_admin_client()
    topics = {
        '_confluent_balancer_partition_samples',
        '_confluent_balancer_api_state',
        '_confluent_balancer_broker_samples',
        '_confluent-telemetry-metrics',
        '_confluent-command',
    }
    return topics.issubset(set(client.list_topics(timeout=1).topics.keys()))


def initialize_topics():
    with Producer(common.INSTANCE):
        with Consumer(common.INSTANCE, common.CONSUMED_TOPICS):
            time.sleep(5)


def wait_for_ssl_ready():
    try:
        client = _create_admin_client()
        metadata = client.list_topics(timeout=5)
        return metadata.cluster_id is not None
    except Exception as e:
        print(f"SSL not ready yet: {e}")
        return False


def _create_admin_client():
    config = {
        "bootstrap.servers": common.INSTANCE['kafka_connect_str'],
        "socket.timeout.ms": 5000,  # Increased for SSL handshake
        "topic.metadata.refresh.interval.ms": 2000,
    }
    auth_config = common.get_authentication_configuration(common.INSTANCE)
    config.update(auth_config)

    return AdminClient(config)
