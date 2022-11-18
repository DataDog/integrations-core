import re


class SonarqubeAPI:
    def __init__(self, log, http, endpoint):
        self._log = log
        self._http = http
        self._endpoint = endpoint

    def get_version(self):
        response = self._make_request('/api/server/version', {})
        return response.text

    def get_projects(self):
        response = self._make_request('/api/components/search', {'qualifiers': 'TRK'})
        return [project['key'] for project in response.json()['components']]

    def get_metrics(self):
        metrics = []
        page = 1
        seen = 0
        total = -1
        not_numeric = 0
        hidden_metrics = 0
        while total == -1 or seen < total:
            response = self._make_request('/api/metrics/search', {'p': page})
            total = response.json()['total']
            for metric in response.json()['metrics']:
                seen += 1
                if not metric['hidden']:
                    if metric['type'] in ['INT', 'FLOAT', 'PERCENT', 'BOOL', 'MILLISEC', 'RATING']:
                        snake_case_domain = (
                            re.sub(
                                r"([a-z\d])([A-Z])",
                                r'\1_\2',
                                re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', metric['domain']),
                            )
                            .replace("-", "_")
                            .lower()
                        )
                        metrics.append('{}.{}'.format(snake_case_domain, metric['key']))
                    else:
                        not_numeric += 1
                        self._log.debug("not_numeric metric: %s", metric)
                else:
                    hidden_metrics += 1
                    self._log.debug("hidden metric: %s", metric)
            page += 1
        self._log.debug("not_numeric: %d", not_numeric)
        self._log.debug("hidden_metrics: %d", hidden_metrics)
        self._log.debug("metrics: %d", len(metrics))
        return metrics

    def get_measures(self, project, metrics):
        response = self._make_request(
            '/api/measures/component', {'component': project, 'metricKeys': ','.join(metrics)}
        )
        return [(measure['metric'], measure['value']) for measure in response.json()['component']['measures']]

    def _make_request(self, url, params):
        endpoint = '{}{}'.format(self._endpoint, url)
        self._log.debug("calling: %s with params: %s", endpoint, params)
        response = self._http.get(endpoint, params=params)
        response.raise_for_status()
        return response
