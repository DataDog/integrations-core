import cm_client


class ClouderaClient:
    def __init__(self, username, password, api_url):
        cm_client.configuration.username = username
        cm_client.configuration.password = password
        self.api_client = cm_client.ApiClient(api_url)

    def query(self, cloudera_api):
        # api_instance = cm_client.cloudera_api(self.api_client)

        raise NotImplemented

    def query_time_series(self, query, from_time, to_time):
        api_instance = cm_client.TimeSeriesResourceApi(self.api_client)
        response = api_instance.query_time_series(_from=from_time, query=query, to=to_time)

        timeseries = response.items[0].time_series

        return timeseries