# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import decimal
import logging
import socket
import time
from itertools import chain

try:
    import datadog_agent
except ImportError:
    from ....stubs import datadog_agent

logger = logging.getLogger(__file__)

# AgentCheck methods to transformer name e.g. set_metadata -> metadata
SUBMISSION_METHODS = {
    'gauge': 'gauge',
    'count': 'count',
    'monotonic_count': 'monotonic_count',
    'rate': 'rate',
    'histogram': 'histogram',
    'historate': 'historate',
    'set_metadata': 'metadata',
    # These submission methods require more configuration than just a name
    # and a value and therefore must be defined as a custom transformer.
    'service_check': '__service_check',
}


def create_submission_transformer(submit_method):
    # During the compilation phase every transformer will have access to all the others and may be
    # passed the first arguments (e.g. name) that will be forwarded the actual AgentCheck methods.
    def get_transformer(_transformers, *creation_args, **modifiers):
        # The first argument of every transformer is a map of named references to collected values.
        def transformer(_sources, *call_args, **kwargs):
            kwargs.update(modifiers)

            # TODO: When Python 2 goes away simply do:
            # submit_method(*creation_args, *call_args, **kwargs)
            submit_method(*chain(creation_args, call_args), **kwargs)

        return transformer

    return get_transformer


def create_extra_transformer(column_transformer, source=None):
    # Every column transformer expects a value to be given but in the post-processing
    # phase the values are determined by references, so to avoid redefining every
    # transformer we just map the proper source to the value.
    if source:

        def transformer(sources, **kwargs):
            return column_transformer(sources, sources[source], **kwargs)

    # Extra transformers that call regular transformers will want to pass values directly.
    else:

        transformer = column_transformer

    return transformer


class ConstantRateLimiter:
    """
    Basic rate limiter that sleeps long enough to ensure the rate limit is not exceeded. Not thread safe.
    """

    def __init__(self, rate_limit_s):
        """
        :param rate_limit_s: rate limit in seconds
        """
        self.rate_limit_s = rate_limit_s
        self.period_s = 1 / rate_limit_s if rate_limit_s > 0 else 0
        self.last_event = 0

    def sleep(self):
        """
        Sleeps long enough to enforce the rate limit
        """
        elapsed_s = time.time() - self.last_event
        sleep_amount = max(self.period_s - elapsed_s, 0)
        time.sleep(sleep_amount)
        self.last_event = time.time()


def resolve_db_host(db_host):
    agent_hostname = datadog_agent.get_hostname()
    if not db_host or db_host in {'localhost', '127.0.0.1'}:
        return agent_hostname

    try:
        host_ip = socket.gethostbyname(db_host)
    except socket.gaierror as e:
        # could be connecting via a unix domain socket
        logger.debug(
            "failed to resolve DB host '%s' due to %r. falling back to agent hostname: %s",
            db_host,
            e,
            agent_hostname,
        )
        return agent_hostname

    try:
        agent_host_ip = socket.gethostbyname(agent_hostname)
        if agent_host_ip == host_ip:
            return agent_hostname
    except socket.gaierror as e:
        logger.debug(
            "failed to resolve agent host '%s' due to socket.gaierror(%s). using DB host: %s",
            agent_hostname,
            e,
            db_host,
        )

    return db_host


def default_json_event_encoding(o):
    if isinstance(o, decimal.Decimal):
        return float(o)
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    raise TypeError
