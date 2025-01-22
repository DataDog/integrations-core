import subprocess
import json


def test_connections():
    result = subprocess.run(["docker", "exec", "compose-agent-1", "agent", "check", "connections", "--json"], check=True, capture_output=True)
    check_json = json.loads(result.stdout)
    submitted_metrics = check_json[0]['aggregator']['metrics']
    for metric_json in submitted_metrics:
        assert metric_json["points"][-1][-1] == 0
