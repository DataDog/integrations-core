import json
import os

import requests

DD_API_KEY = os.environ.get("DD_API_KEY")
DD_APP_KEY = os.environ.get("DD_APP_KEY")

if not DD_API_KEY or not DD_APP_KEY:
    raise RuntimeError("Set DD_API_KEY and DD_APP_KEY in your environment.")

HEADERS = {"DD-API-KEY": DD_API_KEY, "DD-APPLICATION-KEY": DD_APP_KEY, "Content-Type": "application/json"}

DASHBOARD_PATH = os.path.join(os.path.dirname(__file__), "dashboards", "airbyte_otel_overview.json")
MONITOR_PATH = os.path.join(os.path.dirname(__file__), "monitors", "airbyte_otel_long_running_jobs.json")

DASHBOARD_API = "https://api.datadoghq.com/api/v1/dashboard"
MONITOR_API = "https://api.datadoghq.com/api/v1/monitor"


def upload_dashboard():
    with open(DASHBOARD_PATH) as f:
        dashboard = json.load(f)
    resp = requests.post(DASHBOARD_API, headers=HEADERS, json=dashboard)
    print("Dashboard upload status:", resp.status_code)
    print(resp.json())


def upload_monitor():
    with open(MONITOR_PATH) as f:
        monitor = json.load(f)
    # The monitor JSON is a wrapper, extract the 'definition' for the API
    monitor_api_payload = monitor["definition"]
    monitor_api_payload["name"] = monitor["title"]
    monitor_api_payload["tags"] = monitor.get("tags", [])
    resp = requests.post(MONITOR_API, headers=HEADERS, json=monitor_api_payload)
    print("Monitor upload status:", resp.status_code)
    print(resp.json())


if __name__ == "__main__":
    upload_dashboard()
    upload_monitor()
