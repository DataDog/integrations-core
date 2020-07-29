# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import decimal
import json

import requests
import time

import mmh3

import logging

LOGGER = logging.getLogger(__file__)

try:
    import datadog_agent
except ImportError:
    from ..stubs import datadog_agent


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


class eventEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return float(o)
        return super(eventEncoder, self).default(o)


def chunks(items, n):
    for i in range(0, len(items), n):
        yield items[i:i + n]


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
            'message': json.dumps(e, cls=eventEncoder),
            'service': service,
            'ddsource': source,
            'timestamp': timestamp
        }

    for chunk in chunks(events, 100):
        try:
            r = requests.post(f"https://http-intake.logs.datadoghq.com/v1/input",
                              json=[_to_log_event(e) for e in chunk],
                              timeout=60,
                              headers={
                                  'DD-API-KEY': datadog_agent.get_config('api_key')
                              })
            r.raise_for_status()
            LOGGER.debug("submitted %s exec plan events", len(chunk))
        except requests.HTTPError:
            LOGGER.exception("failed to submit exec plan events")
        except Exception:
            LOGGER.exception("failed to submit exec plan events")
