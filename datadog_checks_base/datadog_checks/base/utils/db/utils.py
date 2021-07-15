# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import datetime
import decimal
import logging
import os
import socket
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from itertools import chain

from cachetools import TTLCache

from datadog_checks.base import is_affirmative
from datadog_checks.base.log import get_check_logger

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
        self.rate_limit_s = max(rate_limit_s, 0)
        self.period_s = 1.0 / self.rate_limit_s if self.rate_limit_s > 0 else 0
        self.last_event = 0

    def sleep(self):
        """
        Sleeps long enough to enforce the rate limit
        """
        elapsed_s = time.time() - self.last_event
        sleep_amount = max(self.period_s - elapsed_s, 0)
        time.sleep(sleep_amount)
        self.last_event = time.time()


class RateLimitingTTLCache(TTLCache):
    """
    TTLCache wrapper used for rate limiting by key
    """

    def acquire(self, key):
        """
        :return: True if the key has not yet reached its rate limit
        """
        if len(self) >= self.maxsize:
            return False
        if key in self:
            return False
        self[key] = True
        return True


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


class DBMAsyncJob(object):
    executor = ThreadPoolExecutor()

    """
    Runs Async Jobs
    """

    def __init__(
        self,
        check,
        config_host=None,
        min_collection_interval=15,
        dbms="TODO",
        rate_limit=1,
        run_sync=False,
        enabled=True,
        expected_db_exceptions=(),
        shutdown_callback=None,
        job_name=None,
    ):
        self._check = check
        self._config_host = config_host
        self._min_collection_interval = min_collection_interval
        # map[dbname -> psycopg connection]
        self._log = get_check_logger()
        self._job_loop_future = None
        self._cancel_event = threading.Event()
        self._tags = None
        self._tags_no_db = None
        self._run_sync = None
        self._db_hostname = None
        self._last_check_run = 0
        self._shutdown_callback = shutdown_callback
        self._dbms = dbms
        self._rate_limiter = ConstantRateLimiter(rate_limit)
        self._run_sync = run_sync
        self._enabled = enabled
        self._expected_db_exceptions = expected_db_exceptions
        self._job_name = job_name

    def cancel(self):
        self._cancel_event.set()

    def run_job_loop(self, tags):
        """
        :param tags:
        :return:
        """
        if not self._enabled:
            self._log.debug("[job=%s] Job not enabled.", self._job_name)
            return
        if not self._db_hostname:
            self._db_hostname = resolve_db_host(self._config_host)
        self._tags = tags
        self._tags_str = ','.join(self._tags)
        self._job_tags = self._tags + ["job:{}".format(self._job_name)]
        self._job_tags_str = ','.join(self._job_tags)
        self._last_check_run = time.time()
        if self._run_sync or is_affirmative(os.environ.get('DBM_THREADED_JOB_RUN_SYNC', "false")):
            self._log.debug("Running threaded job synchronously. job=%s", self._job_name)
            self._run_job_rate_limited()
        elif self._job_loop_future is None or not self._job_loop_future.running():
            self._job_loop_future = DBMAsyncJob.executor.submit(self._job_loop)
        else:
            self._log.debug("Job loop already running. job=%s", self._job_name)

    def _job_loop(self):
        try:
            self._log.info("[%s] Starting job loop", self._job_tags_str)
            while True:
                if self._cancel_event.isSet():
                    self._log.info("[%s] Job loop cancelled", self._job_tags_str)
                    self._check.count("dd.{}.async_job.cancel".format(self._dbms), 1, tags=self._job_tags)
                    break
                if time.time() - self._last_check_run > self._min_collection_interval * 2:
                    self._log.info("[%s] Job loop stopping due to check inactivity", self._job_tags_str)
                    self._check.count("dd.{}.async_job.inactive_stop".format(self._dbms), 1, tags=self._job_tags)
                    break
                self._run_job_rate_limited()
        except self._expected_db_exceptions as e:
            self._log.warning(
                "[%s] Job loop database error: %s",
                self._job_tags_str,
                e,
                exc_info=self._log.getEffectiveLevel() == logging.DEBUG,
            )
            self._check.count(
                "dd.{}.async_job.error".format(self._dbms),
                1,
                tags=self._job_tags + ["error:database-{}".format(type(e))],
            )
        except Exception as e:
            self._log.exception("[%s] Job loop crash", self._job_tags_str)
            self._check.count(
                "dd.{}.async_job.error".format(self._dbms),
                1,
                tags=self._job_tags + ["error:crash-{}".format(type(e))],
            )
        finally:
            self._log.info("[%s] Shutting down job loop", self._job_tags_str)
            if self._shutdown_callback:
                self._shutdown_callback()

    def _set_rate_limit(self, rate_limit):
        if self._rate_limiter.rate_limit_s != rate_limit:
            self._rate_limiter = ConstantRateLimiter(rate_limit)

    def _run_job_rate_limited(self):
        self.run_job()
        self._rate_limiter.sleep()

    def run_job(self):
        raise NotImplementedError()
