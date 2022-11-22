from .client import ClouderaClient


def make_api_client(check, instance):
    workload_username = instance.get("workload_username")
    workload_password = instance.get("workload_password")
    api_url = instance.get("api_url")

    try:
        return ClouderaClient(username=workload_username, password=workload_password, api_url=api_url), None
    except Exception as e:
        return None, str(e)
