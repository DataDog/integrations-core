import subprocess
import json


REGULAR_AGENT = {
    'http_status': 1,
    'http_status_fips_server': 1,
}
FIPS_AGENT = {
    'http_status': 0,
    'http_status_fips_server': 1,
}


def _parse_json(payload):
    """
    Convert agent check json to dict of metric_name: value.
    """


def test_connections_regular_agent():
    result = subprocess.run(["docker", "exec", "compose-agent-1", "agent", "check", "connections", "--json"], check=True, capture_output=True)
    check_json = json.loads(result.stdout)
    submitted_metrics = check_json[0]['aggregator']['metrics']
    for metric_json in submitted_metrics:
        assert metric_json["points"][-1][-1] == 0

    assert parsed_json == REGULAR_AGENT
