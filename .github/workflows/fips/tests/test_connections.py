import subprocess

from conftest import AGENT_FIPS_MODE, parse_json

REGULAR_AGENT = {
    'http_status': 1,
    'http_status_fips': 1,
}
FIPS_AGENT = {
    'http_status': 0,
    'http_status_fips': 1,
}


def test_connections():
    result = subprocess.run(["docker", "exec", "compose-agent-1", "agent", "check", "connections", "--json"], check=True, capture_output=True)
    parsed_json = parse_json(result.stdout)
    expected_json = FIPS_AGENT if AGENT_FIPS_MODE else REGULAR_AGENT

    from conftest import debug
    debug()

    assert parsed_json == expected_json
