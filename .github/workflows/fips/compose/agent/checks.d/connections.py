from checks import AgentCheck
from requests.exceptions import SSLError


class HelloCheck(AgentCheck):
    def check(self, instance):
        try:
            self.http.get(instance.get('http_endpoint'), verify=False)
        except SSLError as e:
            self.gauge('http_status', 0)
            self.log.warn(f"Exception when trying to connect to {instance.get('http_endpoint')}: {e}")
        except Exception as e:
            raise RuntimeError(f"Unhandled exception when trying to connect to {instance.get('http_endpoint')}: {e}")
        else:
            self.gauge('http_status', 1)
