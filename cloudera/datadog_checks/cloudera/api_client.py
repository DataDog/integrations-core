from abc import abstractmethod

import cm_client


class ApiClient:
    def __init__(self, check, api_client):
        self._check = check
        self._log = check.log
        self._api_client = api_client

    @abstractmethod
    def collect_data(self):
        raise NotImplementedError

    def run_timeseries_query(self, query):
        time_series_resource_api = cm_client.TimeSeriesResourceApi(self._api_client)
        # Note: by default query_time_series() sets the optional `to_time`
        # param to `now` and `_from_time` param to 5 minutes before now.
        query_time_series_response = time_series_resource_api.query_time_series(query=query)
        # There is always only one item in response list `items`
        for item in query_time_series_response:
            if not item.data:
                self._log.debug(f"Data for entity {item.metadata.entity_name} is empty")
                continue

            self._log.debug("item: %s", item)
            value = item.data[0].value
            attributes = item.metadata.attributes

            # TODO: Add custom tags to this
            tags = []
            for datadog_tag, attribute in query['tags']:
                try:
                    tags.append(f"{datadog_tag}:{attributes[attribute]}")
                except Exception:
                    self._log.debug(f"no {datadog_tag} tag for metric {item.metadata.entity_name}")

            category = attributes['category'].lower()
            self._log.debug("metric: %s", f"{category}.{query['metric_name']}")
            self._log.debug("value: %s", value)
            self._log.debug("tags: %s", tags)
            self._check.gauge(f"{category}.{query['metric_name']}", value, tags=tags)
