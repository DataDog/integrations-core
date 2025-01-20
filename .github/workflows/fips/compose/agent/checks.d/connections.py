from checks import AgentCheck


class HelloCheck(AgentCheck):
    def check(self, instance):
        try:
            self.http.get(instance.get('http_endpoint'))
        except Exception as e:
            self.gauge('http_status', 1)
            print(f"Exception when trying to connect to {instance.get('http_endpoint')}: {e}")
        else:
            self.gauge('https_status', 0)
