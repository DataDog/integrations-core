# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import copy
import os
import socket

from confluent_kafka.admin import AdminClient

from datadog_checks.dev import get_docker_hostname
from datadog_checks.dev.utils import get_metadata_metrics

HERE = os.path.dirname(os.path.abspath(__file__))
HOST = get_docker_hostname()
HOST_IP = socket.gethostbyname(HOST)
KAFKA_CONNECT_STR = f'{HOST_IP}:9092'
CONSUMED_TOPICS = ['marvel', 'dc']
TOPICS = ['marvel', 'dc', 'unconsumed_topic']
PARTITIONS = [0, 1]
BROKER_METRICS = ['kafka.broker_offset']
CONSUMER_METRICS = ['kafka.consumer_offset', 'kafka.consumer_lag']
AUTHENTICATION = os.environ.get('AUTHENTICATION', 'noauth')
DOCKER_IMAGE_PATH = os.path.join(HERE, 'docker', AUTHENTICATION, "docker-compose.yaml")

metrics = BROKER_METRICS + CONSUMER_METRICS


CERTIFICATE_DIR = os.path.join(os.path.dirname(__file__), 'docker', 'ssl', 'certificate')
ROOT_CERTIFICATE = os.path.join(CERTIFICATE_DIR, 'caroot.pem')
CERTIFICATE = os.path.join(CERTIFICATE_DIR, 'cert.pem')
PRIVATE_KEY = os.path.join(CERTIFICATE_DIR, 'key.pem')
PRIVATE_KEY_PASSWORD = 'secret'

E2E_METADATA = {
    'custom_hosts': [('kafka1', '127.0.0.1'), ('kafka2', '127.0.0.1')],
    'docker_volumes': [
        f'{HERE}/docker/ssl/certificate:/tmp/certificate',
        f'{HERE}/docker/kerberos/kdc/krb5_agent.conf:/etc/krb5.conf',
    ],
}

if AUTHENTICATION == "ssl":
    INSTANCE = {
        'kafka_connect_str': "localhost:9092",
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
        'security_protocol': 'SSL',
        'tls_cert': CERTIFICATE,
        'tls_private_key': PRIVATE_KEY,
        'tls_private_key_password': PRIVATE_KEY_PASSWORD,
        'tls_ca_cert': ROOT_CERTIFICATE,
    }
elif AUTHENTICATION == "kerberos":
    INSTANCE = {
        'kafka_connect_str': "localhost:9092",
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
        "sasl_mechanism": "GSSAPI",
        "sasl_kerberos_service_name": "kafka",
        "security_protocol": "SASL_PLAINTEXT",
        # Real path will be replaced once the temp dir will be created in `dd_environment`
        "sasl_kerberos_keytab": "{}/localhost.key",
        "sasl_kerberos_principal": "kafka/localhost",
    }
else:
    INSTANCE = {
        'kafka_connect_str': KAFKA_CONNECT_STR,
        'tags': ['optional:tag1'],
        'consumer_groups': {'my_consumer': {'marvel': [0]}},
    }

E2E_INSTANCE = copy.deepcopy(INSTANCE)

if AUTHENTICATION == "ssl":
    E2E_INSTANCE["tls_cert"] = "/tmp/certificate/cert.pem"
    E2E_INSTANCE["tls_private_key"] = "/tmp/certificate/key.pem"
    E2E_INSTANCE["tls_ca_cert"] = "/tmp/certificate/caroot.pem"
elif AUTHENTICATION == "kerberos":
    E2E_INSTANCE["sasl_kerberos_keytab"] = "/var/lib/secret/localhost.key"


def get_cluster_id():
    config = {
        "bootstrap.servers": INSTANCE['kafka_connect_str'],
        "socket.timeout.ms": 1000,
        "topic.metadata.refresh.interval.ms": 2000,
    }
    config.update(get_authentication_configuration(INSTANCE))
    client = AdminClient(config)
    return client.list_topics(timeout=5).cluster_id


def assert_check_kafka(aggregator, consumer_groups):
    cluster_id = get_cluster_id()
    for name, consumer_group in consumer_groups.items():
        for topic, partitions in consumer_group.items():
            for partition in partitions:
                tags = [f"topic:{topic}", f"partition:{partition}", "kafka_cluster_id:" + cluster_id] + [
                    'optional:tag1'
                ]
                for mname in BROKER_METRICS:
                    aggregator.assert_metric(mname, tags=tags, count=1)

                for mname in CONSUMER_METRICS:
                    aggregator.assert_metric(
                        mname,
                        tags=tags + [f"consumer_group:{name}"],
                        count=1,
                    )

    aggregator.assert_all_metrics_covered()
    aggregator.assert_metrics_using_metadata(get_metadata_metrics())


def get_authentication_configuration(instance):
    config = {}

    if AUTHENTICATION != "noauth":
        config["security.protocol"] = instance.get("security_protocol").lower()

        if AUTHENTICATION == "ssl":
            config.update(
                {
                    "ssl.ca.location": instance.get("tls_ca_cert"),
                    "ssl.certificate.location": instance.get("tls_cert"),
                    "ssl.key.location": instance.get("tls_private_key"),
                    "ssl.key.password": instance.get("tls_private_key_password"),
                }
            )

        if AUTHENTICATION == "kerberos":
            config.update(
                {
                    "sasl.mechanism": instance.get("sasl_mechanism"),
                    "sasl.kerberos.service.name": instance.get("sasl_kerberos_service_name"),
                    "sasl.kerberos.keytab": instance.get("sasl_kerberos_keytab"),
                    "sasl.kerberos.principal": instance.get("sasl_kerberos_principal"),
                }
            )

    return config
