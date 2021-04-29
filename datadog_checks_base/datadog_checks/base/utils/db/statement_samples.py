import datetime
import decimal
import itertools
import logging

import requests
from requests.adapters import HTTPAdapter, Retry

from datadog_checks.base.utils.serialization import json

try:
    import datadog_agent

    using_stub_datadog_agent = False
except ImportError:
    from ....stubs import datadog_agent

    using_stub_datadog_agent = True

logger = logging.getLogger(__file__)


def default_encoding(o):
    if isinstance(o, decimal.Decimal):
        return float(o)
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    raise TypeError


def _chunks(items, n):
    it = iter(items)
    while True:
        chunk = tuple(itertools.islice(it, n))
        if not chunk:
            return
        yield chunk


def _new_api_session(api_key):
    http = requests.Session()
    http.mount(
        "https://", HTTPAdapter(max_retries=Retry(connect=2, read=2, redirect=2, status=2, method_whitelist=['POST']))
    )
    http.headers.update({'DD-API-KEY': api_key})
    return http


def _event_intake_url(host):
    if host.endswith("."):
        host = host[:-1]
    if not host.startswith("https://"):
        host = "https://" + host
    return host + "/v1/input"


default_dbm_url = "dbquery-http-intake.logs.datadoghq.com"


def _load_event_endpoints_from_config(config_prefix, default_url):
    """
    Returns a list of requests sessions and their endpoint urls [(http, url), ...]
    Requests sessions are initialized the first time this is called and reused thereafter
    :return: list of (http, url)

    :param config_prefix:
    :param default_url:
    :return:
    """
    url = _event_intake_url(datadog_agent.get_config('{}.dd_url'.format(config_prefix)) or default_url)
    endpoints = [(_new_api_session(datadog_agent.get_config('api_key')), url)]
    logger.debug("initializing event endpoints from %s. url=%s", config_prefix, url)

    for additional_endpoint in datadog_agent.get_config('{}.additional_endpoints'.format(config_prefix)) or []:
        api_key, host = additional_endpoint.get('api_key'), additional_endpoint.get('host')
        missing_keys = [k for k, v in [('api_key', api_key), ('host', host)] if not v]
        if missing_keys:
            logger.warning(
                "invalid event endpoint found in %s.additional_endpoints. missing required keys %s",
                config_prefix,
                ', '.join(missing_keys),
            )
            continue
        url = _event_intake_url(host)
        endpoints.append((_new_api_session(api_key), url))
        logger.debug("initializing additional event endpoint from %s. url=%s", config_prefix, url)

    return endpoints


class StatementSamplesClient:
    def __init__(self):
        self._endpoints = _load_event_endpoints_from_config("database_monitoring", default_dbm_url)

    def submit_events(self, events):
        """
        Submit the statement sample events to the event intake
        :return: submitted_count, failed_count
        """
        submitted_count = 0
        failed_count = 0
        for chunk in _chunks(events, 100):
            for http, url in self._endpoints:
                try:
                    r = http.request(
                        'post',
                        url,
                        data=json.dumps(chunk, default=default_encoding),
                        timeout=5,
                        headers={'Content-Type': 'application/json'},
                    )
                    r.raise_for_status()
                    logger.debug("Submitted %s statement samples to %s", len(chunk), url)
                    submitted_count += len(chunk)
                except requests.HTTPError as e:
                    logger.warning("Failed to submit statement samples to %s: %s", url, e)
                    failed_count += len(chunk)
                except Exception:
                    logger.exception("Failed to submit statement samples to %s", url)
                    failed_count += len(chunk)
        return submitted_count, failed_count


class StubStatementSamplesClient:
    def __init__(self):
        self._payloads = []

    def submit_events(self, events):
        events = list(events)
        self._payloads.append(json.dumps(events, default=default_encoding))
        return len(events), 0

    def get_events(self):
        events = []
        for p in self._payloads:
            events.extend(json.loads(p))
        return events


statement_samples_client = StubStatementSamplesClient() if using_stub_datadog_agent else StatementSamplesClient()
