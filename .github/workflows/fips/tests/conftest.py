import json
import os

AGENT_FIPS_MODE = 1 if "fips" in os.getenv("AGENT_TYPE") else 0
REGULAR_AGENT = set((
    ('http_status_fips', 1),
    ('ssh_status_fips', 1),
    ('http_status', 1),
    ('ssh_status', 0),  # paramiko does not support non FIPS ciphers OOTB
    ('ssl_status', 1),
    ('cryptography_status', 1),
    ))
FIPS_AGENT = set((
    ('http_status_fips', 1),
    ('ssh_status_fips', 1),
    ('http_status', 0),
    ('ssh_status', 0),
    ('ssl_status', 0),
    ('cryptography_status', 0),
    ))

WORKAROUND = ("-e", "OPENSSL_CONF=/opt/datadog-agent/embedded/ssl/openssl.cnf", "-e", "OPENSSL_MODULES=/opt/datadog-agent/embedded/lib/ossl-modules") if os.environ.get("RUNNER_OS") == "Linux" else ("-e", "OPENSSL_CONF=C:/Program Files/Datadog/Datadog Agent/embedded3/ssl/openssl.cnf", "-e", "OPENSSL_MODULES=C:/Program Files/Datadog/Datadog Agent/embedded3/lib/ossl-modules")


def parse_json(payload) -> set:
    """
    Convert agent check json to a set of (metric_name, value).
    """
    parsed_json = set()
    # The payload may start with a message like "Multiple instances found". 
    # Therefore, we need to split the payload and load the json objects.
    if not payload.startswith(b'['):
        payload = b'['+payload.split(b'[', maxsplit=1)[1]
    check_json = json.loads(payload)
    # The suffixes depend on the order of the defined instances in the config.
    for instance, suffix in zip(check_json, ("", "_fips")):
        for metric_json in instance['aggregator']['metrics']:
            parsed_json.add((metric_json["metric"]+suffix,int(metric_json["points"][-1][-1])))
    return parsed_json

