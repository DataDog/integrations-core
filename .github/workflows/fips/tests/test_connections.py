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
    for instance, suffix in zip(payload, ("", "_fips")):
        submitted_metrics = instance['aggregator']['metrics']
        for metric_json in submitted_metrics:
            parsed_json[metric_json["metric"]+suffix] = int(metric_json["points"][-1][-1])
        return parsed_json


def test_connections():
    result = subprocess.run(["docker", "exec", "compose-agent-1", "agent", "check", "connections", "--json"], check=True, capture_output=True)
    check_json = json.loads(result.stdout)
    parsed_json = _parse_json(check_json)

    assert parsed_json == FIPS_AGENT if AGENT_FIPS_MODE else REGULAR_AGENT
