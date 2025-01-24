from checks import AgentCheck


class HelloCheck(AgentCheck):
    def check(self, instance):
        try:
            self.http.get(instance.get('http_endpoint'), verify=False)
        except Exception as e:
            self.gauge('http_status', 0)
            self.log.warn(f"Exception when trying to connect to {instance.get('http_endpoint')}: {e}")
            raise RuntimeError(f"Exception when trying to connect to {instance.get('http_endpoint')}: {e}")
        else:
            self.gauge('https_status', 1)
