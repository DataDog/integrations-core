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
        return query_time_series_response.items[0].time_series
