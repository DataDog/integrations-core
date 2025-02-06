import subprocess

from conftest import (AGENT_FIPS_MODE, FIPS_AGENT, REGULAR_AGENT, WORKAROUND,
                      parse_json)


def test_connections():
    result = subprocess.run(["docker", "exec", "compose-agent-1", "agent", "check", "connections", "--json"], check=True, capture_output=True)
    parsed_json = parse_json(result.stdout)
    expected_json = FIPS_AGENT if AGENT_FIPS_MODE else REGULAR_AGENT

    assert parsed_json.issubset(expected_json)


def test_libraries():
    result = subprocess.run(["docker", "exec", *WORKAROUND, "compose-agent-1", "agent", "check", "libraries", "--json"], check=True, capture_output=True)
    parsed_json = parse_json(result.stdout)
    expected_json = FIPS_AGENT if AGENT_FIPS_MODE else REGULAR_AGENT

    assert parsed_json.issubset(expected_json)
