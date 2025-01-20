import subprocess


def test_connections():
    subprocess.run(["docker", "exec", "compose-agent-1", "agent", "check", "connections", "--json"], check=True)
    pass
