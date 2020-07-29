# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import decimal
import json
import logging

import mmh3
import requests
import time
from requests.adapters import HTTPAdapter
from urllib3 import Retry

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent

LOGGER = logging.getLogger(__file__)


def compute_sql_signature(normalized_query):
    """
    Given an already obfuscated & normalized SQL query, generate its 64-bit hex signature.
    """
    if not normalized_query:
        return None
    return format(mmh3.hash64(normalized_query, signed=False)[0], 'x')


def compute_exec_plan_signature(normalized_json_plan):
    """
    Given an already normalized json string query execution plan, generate its 64-bit hex signature.
    """
    if not normalized_json_plan:
        return None
    with_sorted_keys = json.dumps(json.loads(normalized_json_plan), sort_keys=True)
    return format(mmh3.hash64(with_sorted_keys, signed=False)[0], 'x')


class EventEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(EventEncoder, self).default(o)


def chunks(items, n):
    for i in range(0, len(items), n):
        yield items[i:i + n]


LOGS_HTTP_INTAKE_ENDPOINT = "https://http-intake.logs.datadoghq.com/v1/input"


def init_http():
    adapter = HTTPAdapter(max_retries=Retry(connect=2, read=2, redirect=2, status=2, method_whitelist=['POST']))
    http = requests.Session()
    http.mount("https://", adapter)
    return http


http = init_http()


def submit_exec_plan_events(events, tags, source):
    """
    Submit the execution plan events to the event intake
    https://docs.datadoghq.com/api/v1/logs/#send-logs
    """
    ddtags = ','.join(tags)
    hostname = datadog_agent.get_hostname()
    service = next((t for t in tags if t.startswith('service:')), 'service:{}'.format(source))[len('service:'):]
    timestamp = time.time() * 1000

    def _to_log_event(e):
        return {
            'ddtags': ddtags,
            'hostname': hostname,
            'message': json.dumps(e, cls=EventEncoder),
            'service': service,
            'ddsource': source,
            'timestamp': timestamp
        }

    for chunk in chunks(events, 100):
        try:
            r = http.request('post', LOGS_HTTP_INTAKE_ENDPOINT,
                             data=json.dumps([_to_log_event(e) for e in chunk]),
                             timeout=5,
                             headers={
                                 'DD-API-KEY': datadog_agent.get_config('api_key'),
                                 'Content-Type': 'application/json'
                             })
            r.raise_for_status()
            LOGGER.debug("submitted %s exec plan events", len(chunk))
        except requests.HTTPError:
            LOGGER.exception("failed to submit exec plan events")
        except Exception:
            LOGGER.exception("failed to submit exec plan events")
