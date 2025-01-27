import subprocess

from conftest import AGENT_FIPS_MODE, parse_json

REGULAR_AGENT = {
    'ssl_status': 1,
    'cryptography_status': 1,
}
FIPS_AGENT = {
    'ssl_status': 0,
    'cryptography_status': 0,
}


def test_libraries():
    result = subprocess.run(["docker", "exec", "-e", "OPENSSL_CONF=/opt/datadog-agent/embedded/ssl/openssl.cnf", "-e", "OPENSSL_MODULES=/opt/datadog-agent/embedded/lib/ossl-modules", "compose-agent-1", "agent", "check", "libraries", "--json"], check=True, capture_output=True)
    parsed_json = parse_json(result.stdout)
    expected_json = FIPS_AGENT if AGENT_FIPS_MODE else REGULAR_AGENT

    assert parsed_json == expected_json
