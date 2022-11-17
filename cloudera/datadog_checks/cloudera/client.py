import cm_client


class ClouderaClient:
    def __init__(self, username, password, api_url):
        cm_client.configuration.username = username
        cm_client.configuration.password = password
        self.api_client = cm_client.ApiClient(api_url)

    def run_query(self, cloudera_api_class, cloudera_api_method, **kwargs):
        # Create an instance of cloudera_api_class
        api_instance = getattr(cm_client, cloudera_api_class)(self.api_client)

        # Run cloudera_api_method to query for metrics and service checks
        response = getattr(api_instance, cloudera_api_method)(**kwargs)

        return response.items

    def run_timeseries_query(self, query, from_time, to_time):
        api_instance = cm_client.TimeSeriesResourceApi(self.api_client)
        response = api_instance.query_time_series(_from=from_time, query=query, to=to_time)

        # There is always only one item in list `items`
        return response.items[0].time_series

    def get_cluster_tags(self):

        raise NotImplemented