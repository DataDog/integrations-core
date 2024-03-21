# (C) Datadog, Inc. 2023-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from confluent_kafka.admin import AdminClient

'''
This is a simple script that can be used to start a barebones
AdminClient similar to the integration to test connections.

The client will attempt to connect and then query for consumer groups.
'''

# EDITME
kafka_connect_str = ""
request_timeout_ms = 5000
tls_ca_cert = ""
tls_cert = ""
tls_private_key = ""
tls_private_key_password = ""
tls_validate_hostname = ""
crlfile = ""
tls_verify = "true"
sasl_mechanism = ""
sasl_plain_username = ""
sasl_plain_password = ""
sasl_kerberos_keytab = ""
sasl_kerberos_principal = ""
sasl_kerberos_service_name = ""
security_protocol = ""


def __get_authentication_config():
    config = {
        "security.protocol": security_protocol.lower(),
    }

    extras_parameters = {
        "ssl.ca.location": tls_ca_cert,
        "ssl.certificate.location": tls_cert,
        "ssl.key.location": tls_private_key,
        "ssl.key.password": tls_private_key_password,
        "ssl.endpoint.identification.algorithm": "https" if tls_validate_hostname else "none",
        "ssl.crl.location": crlfile,
        "enable.ssl.certificate.verification": tls_verify,
        "sasl.mechanism": sasl_mechanism,
        "sasl.username": sasl_plain_username,
        "sasl.password": sasl_plain_password,
        "sasl.kerberos.keytab": sasl_kerberos_keytab,
        "sasl.kerberos.principal": sasl_kerberos_principal,
        "sasl.kerberos.service.name": sasl_kerberos_service_name,
    }

    for key, value in extras_parameters.items():
        if value:
            config[key] = value

    return config


def create_client():
    config = {
        "bootstrap.servers": kafka_connect_str,
        "socket.timeout.ms": request_timeout_ms,
        "client.id": "dd-agent",
    }
    config.update(__get_authentication_config())

    for key, value in config.items():
        new_value = "*****" if "password" in key else value
        print(f"{key}={new_value}")

    return AdminClient(config)


def main():
    admin_client = create_client()
    print("Connecting to AdminClient")
    future = admin_client.list_consumer_groups()
    results = future.result()
    for valid_consumer_group in results.valid:
        print("Found consumer group: %s" % valid_consumer_group.group_id)
    print("Done")


if __name__ == "__main__":
    main()
