import subprocess

from conftest import (AGENT_FIPS_MODE, FIPS_AGENT, REGULAR_AGENT, WORKAROUND,
                      parse_json)


def test_connections():
    result = subprocess.run(["docker", "exec", "compose-agent-1", "agent", "check", "connections", "--json"], check=True, capture_output=True)
    parsed_metrics = parse_json(result.stdout)
    expected_metrics = FIPS_AGENT if AGENT_FIPS_MODE else REGULAR_AGENT

    assert parsed_metrics == expected_metrics["connections"]


def test_libraries():
    result = subprocess.run(["docker", "exec", "compose-agent-1", "agent", "check", "libraries", "--json"], check=True, capture_output=True)
    parsed_metrics = parse_json(result.stdout)
    expected_metrics = FIPS_AGENT if AGENT_FIPS_MODE else REGULAR_AGENT

    assert parsed_metrics == expected_metrics["libraries"]
