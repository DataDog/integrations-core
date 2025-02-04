from checks import AgentCheck
from requests.exceptions import SSLError
import paramiko


class HelloCheck(AgentCheck):
    def check(self, instance):
        host = instance.get('host')
        http_port = instance.get('http_port')
        ssh_port = instance.get('ssh_port')

        http_endpoint = f"https://{host}:{http_port}"
        ssh_endpoint = f"ssh://{host}:{ssh_port}"

        # Test connection with the HTTPS endpoint
        try:
            self.http.get(http_endpoint, verify=False)
        except SSLError as e:
            self.gauge('http_status', 0)
            self.log.warn(f"Exception when trying to connect to {http_endpoint}: {e}")
        else:
            self.gauge('http_status', 1)

        # Test connection with the SSH endpoint
        try:
            transport = paramiko.Transport(host, int(ssh_port))
            transport.connect()
        except paramiko.ssh_exception.SSHException as e:
            self.gauge('ssh_status', 0)
            self.log.info(f"Exception when trying to connect to {ssh_endpoint}: {e}")
        except paramiko.ssh_exception.IncompatiblePeer as e:
            self.gauge('ssh_status', 0)
            self.log.info(f"Exception when trying to connect to {ssh_endpoint}: {e}")
        else:
            self.gauge('ssh_status', 1)
