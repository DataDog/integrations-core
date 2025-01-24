import subprocess
import json
import os

AGENT_FIPS_MODE = 1 if "fips" in os.getenv("AGENT_TYPE") else 0

REGULAR_AGENT = {
    'http_status': 1,
    'http_status_fips': 1,
}
FIPS_AGENT = {
    'http_status': 0,
    'http_status_fips': 1,
}


def _parse_json(payload):
    """
    Convert agent check json to dict of metric_name: value.
    """
    parsed_json = {}
    # The payload may start with a message like "Multiple instances found". 
    # Therefore, we need to split the payload and load the json objects.
    if not payload.startswith(b'['):
        payload = b'['+payload.split(b'[', maxsplit=1)[1]
    check_json = json.loads(payload)
    # The suffixes depend on the order of the defined instances in the config.
    for instance, suffix in zip(check_json, ("_fips", "")):
        for metric_json in instance['aggregator']['metrics']:
            parsed_json[metric_json["metric"]+suffix] = int(metric_json["points"][-1][-1])
    return parsed_json


def test_connections():
    result = subprocess.run(["docker", "exec", "compose-agent-1", "agent", "check", "connections", "--json"], check=True, capture_output=True)
    parsed_json = _parse_json(result.stdout)
    expected_json = FIPS_AGENT if AGENT_FIPS_MODE else REGULAR_AGENT

    assert parsed_json == expected_json
