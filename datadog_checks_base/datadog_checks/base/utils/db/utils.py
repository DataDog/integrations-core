# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import contextlib
import datetime
import decimal
import functools
import logging
import os
import socket
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from enum import Enum, auto
from ipaddress import IPv4Address
from typing import Any, Callable, Dict, List, Optional, Tuple, Union  # noqa: F401

from cachetools import TTLCache

from datadog_checks.base import is_affirmative
from datadog_checks.base.agent import datadog_agent
from datadog_checks.base.log import get_check_logger
from datadog_checks.base.utils.common import to_native_string
from datadog_checks.base.utils.db.types import Transformer  # noqa: F401
from datadog_checks.base.utils.format import json
from datadog_checks.base.utils.tracing import INTEGRATION_TRACING_SERVICE_NAME, tracing_enabled

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
    'send_log': '__send_log',
}


def _traced_dbm_async_job_method(f):
    integration_tracing, _ = tracing_enabled()
    if integration_tracing:
        try:
            from ddtrace import tracer

            @functools.wraps(f)
            def wrapper(self, *args, **kwargs):
                with tracer.trace(
                    # match the same primary operation name as the regular integration tracing so that these async job
                    # resources appear in the resource list alongside the main check resource
                    "run",
                    service=INTEGRATION_TRACING_SERVICE_NAME,
                    resource="{}.{}".format(self._check.name, self._job_name),
                ) as span:
                    span.set_tag('_dd.origin', INTEGRATION_TRACING_SERVICE_NAME)
                    self.run_job()

            return wrapper
        except Exception:
            return f
    return f


def create_submission_transformer(submit_method):
    # type: (Any) -> Callable[[Any, Any, Any], Callable[[Any, List, Dict], Callable[[Any, Any, Any], Transformer]]]
    # During the compilation phase every transformer will have access to all the others and may be
    # passed the first arguments (e.g. name) that will be forwarded the actual AgentCheck methods.
    def get_transformer(_transformers, *creation_args, **modifiers):
        # type: (List[Transformer], Tuple, Dict[str, Any]) -> Transformer
        # The first argument of every transformer is a map of named references to collected values.
        def transformer(_sources, *call_args, **kwargs):
            # type: (Dict[str, Any], Tuple[str, Any], Dict[str, Any]) -> None
            kwargs.update(modifiers)

            submit_method(*creation_args, *call_args, **kwargs)

        return transformer

    return get_transformer


def create_extra_transformer(column_transformer, source=None):
    # type: (Transformer, str) -> Transformer
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

    def update_last_time_and_sleep(self):
        """
        Sleeps long enough to enforce the rate limit
        """
        elapsed_s = time.time() - self.last_event
        sleep_amount = max(self.period_s - elapsed_s, 0)
        time.sleep(sleep_amount)
        self.update_last_time()

    def shall_execute(self):
        elapsed_s = time.time() - self.last_event
        return elapsed_s >= self.period_s

    def update_last_time(self):
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
    if db_host and db_host.endswith('.local'):
        return db_host

    agent_hostname = datadog_agent.get_hostname()
    if not db_host or db_host in {'localhost', '127.0.0.1'} or db_host.startswith('/'):
        return agent_hostname

    try:
        host_ip = socket.gethostbyname(db_host)
    except (socket.gaierror, UnicodeError) as e:
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
    except (socket.gaierror, UnicodeError) as e:
        logger.debug(
            "failed to resolve agent host '%s' due to socket.gaierror(%s). using DB host: %s",
            agent_hostname,
            e,
            db_host,
        )

    return db_host


def get_agent_host_tags():
    """
    Get the tags from the agent host and return them as a list of strings.
    """
    result = []
    host_tags = datadog_agent.get_host_tags()
    if not host_tags:
        return result
    try:
        tags_dict = json.decode(host_tags) or {}
        for key, value in tags_dict.items():
            if isinstance(value, list):
                result.extend(value)
            else:
                raise ValueError(
                    'Failed to parse {} tags from the agent host because {} is not a list'.format(key, value)
                )
    except Exception as e:
        raise ValueError('Failed to parse tags from the agent host: {}. Error: {}'.format(host_tags, str(e)))
    return result


def default_json_event_encoding(o):
    if isinstance(o, decimal.Decimal):
        return float(o)
    if isinstance(o, (datetime.date, datetime.datetime)):
        return o.isoformat()
    if isinstance(o, IPv4Address):
        return str(o)
    if isinstance(o, bytes):
        return o.decode('utf-8')
    raise TypeError


def obfuscate_sql_with_metadata(query, options=None, replace_null_character=False):
    """
    Obfuscate a SQL query and return the obfuscated query and metadata.
    :param str query: The SQL query to obfuscate.
    :param dict options: Obfuscation options to pass to the obfuscator.
    :param bool replace_null_character: Whether to replace embedded null characters \x00 before obfuscating.
        Note: Setting this parameter to true involves an extra string traversal and copy.
        Do set this to true if the database allows embedded null characters in text fields, for example SQL Server.
        Otherwise obfuscation will fail if the query contains embedded null characters.
    :return: A dict containing the obfuscated query and metadata.
    :rtype: dict
    """
    if not query:
        return {'query': '', 'metadata': {}}

    if replace_null_character:
        # replace embedded null characters \x00 before obfuscating
        query = query.replace('\x00', '')

    statement = datadog_agent.obfuscate_sql(query, options)
    # The `obfuscate_sql` testing stub returns bytes, so we have to handle that here.
    # The actual `obfuscate_sql` method in the agent's Go code returns a JSON string.
    statement = to_native_string(statement.strip())

    # Older agents may not have the new metadata API which returns a JSON string, so we must support cases where
    # newer integrations are running on an older agent. We use this "shortcut" to determine if we've received
    # a JSON string to avoid throwing excessive exceptions. We found that orjson leaks memory when failing
    # to parse these strings which are not valid json. Note, this condition is only relevant for integrations
    # running on agent versions < 7.34
    if not statement.startswith('{'):
        return {'query': statement, 'metadata': {}}

    statement_with_metadata = json.decode(statement)
    metadata = statement_with_metadata.get('metadata', {})
    tables = metadata.pop('tables_csv', None)
    tables = [table.strip() for table in tables.split(',') if table != ''] if tables else None
    statement_with_metadata['metadata']['tables'] = tables
    return statement_with_metadata


class DBMAsyncJob(object):
    # Set an arbitrary high limit so that dbm async jobs (which aren't CPU bound) don't
    # get artificially limited by the default max_workers count. Note that since threads are
    # created lazily, it's safe to set a high maximum
    executor = ThreadPoolExecutor(100000)

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
        """
        Send a signal to cancel the job loop asynchronously.
        """
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
            self._run_sync_job_rate_limited()
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
                    self._check.count("dd.{}.async_job.cancel".format(self._dbms), 1, tags=self._job_tags, raw=True)
                    break
                if time.time() - self._last_check_run > self._min_collection_interval * 2:
                    self._log.info("[%s] Job loop stopping due to check inactivity", self._job_tags_str)
                    self._check.count(
                        "dd.{}.async_job.inactive_stop".format(self._dbms), 1, tags=self._job_tags, raw=True
                    )
                    break
                if self._check.should_profile_memory():
                    self._check.profile_memory(
                        self._run_job_rate_limited,
                        namespaces=[self._check.name, self._job_name],
                        extra_tags=self._job_tags,
                    )
                else:
                    self._run_job_rate_limited()
        except Exception as e:
            if self._cancel_event.isSet():
                # canceling can cause exceptions if the connection is closed the middle of the check run
                # in this case we still want to report it as a cancellation instead of a crash
                self._log.debug("[%s] Job loop error after cancel: %s", self._job_tags_str, e)
                self._log.info("[%s] Job loop cancelled", self._job_tags_str)
                self._check.count("dd.{}.async_job.cancel".format(self._dbms), 1, tags=self._job_tags, raw=True)
            elif isinstance(e, self._expected_db_exceptions):
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
                    raw=True,
                )
            else:
                self._log.exception("[%s] Job loop crash", self._job_tags_str)
                self._check.count(
                    "dd.{}.async_job.error".format(self._dbms),
                    1,
                    tags=self._job_tags + ["error:crash-{}".format(type(e))],
                    raw=True,
                )
        finally:
            self._log.info("[%s] Shutting down job loop", self._job_tags_str)
            if self._shutdown_callback:
                self._shutdown_callback()

    def _set_rate_limit(self, rate_limit):
        if self._rate_limiter.rate_limit_s != rate_limit:
            self._rate_limiter = ConstantRateLimiter(rate_limit)

    def _run_sync_job_rate_limited(self):
        if self._rate_limiter.shall_execute():
            self._rate_limiter.update_last_time()
            self._run_job_traced()

    def _run_job_rate_limited(self):
        try:
            self._run_job_traced()
        except:
            raise
        finally:
            if not self._cancel_event.isSet():
                self._rate_limiter.update_last_time_and_sleep()
            else:
                self._rate_limiter.update_last_time()

    @_traced_dbm_async_job_method
    def _run_job_traced(self):
        return self.run_job()

    def run_job(self):
        raise NotImplementedError()


@contextlib.contextmanager
def tracked_query(check, operation, tags=None):
    """
    A simple context manager that tracks the time spent in a given query operation

    The intention is to use this for context manager is to wrap the execution of a query,
    that way the time spent waiting for query execution can be tracked as a metric. For example,
    '''
    with tracked_query(check, "my_metric_query", tags):
        cursor.execute(query)
    '''

    if debug_stats_kwargs is defined on the check instance,
    it will be called to set additional kwargs when submitting the metric.

    :param check: The check instance
    :param operation: The name of the query operation being performed.
    :param tags: A list of tags to apply to the metric.
    """
    start_time = time.time()
    stats_kwargs = {}
    if hasattr(check, 'debug_stats_kwargs'):
        stats_kwargs = dict(check.debug_stats_kwargs())
    stats_kwargs['tags'] = stats_kwargs.get('tags', []) + ["operation:{}".format(operation)] + (tags or [])
    stats_kwargs['raw'] = True  # always submit as raw to ignore any defined namespace prefix
    yield
    elapsed_ms = (time.time() - start_time) * 1000
    check.histogram("dd.{}.operation.time".format(check.name), elapsed_ms, **stats_kwargs)


class TagType(Enum):
    """Enum for different types of tags"""

    KEYLESS = auto()


class TagManager:
    """
    Manages tags for a check. Tags are stored as a dictionary of key-value pairs
    for key-value tags and as a list of values for keyless tags useful for easy update and deletion.
    There's an internal cache of the tag list to avoid generating the list of tag strings
    multiple times.
    """

    def __init__(self) -> None:
        self._tags: Dict[Union[str, TagType], List[str]] = {}
        self._cached_tag_list: Optional[tuple[str, ...]] = None
        self._keyless: TagType = TagType.KEYLESS

    def set_tag(self, key: Optional[str], value: str, replace: bool = False) -> None:
        """
        Set a tag with the given key and value.
        If key is None or empty, the value is stored as a keyless tag.
        Args:
            key (str): The tag key, or None/empty for keyless tags
            value (str): The tag value
            replace (bool): If True, replaces all existing values for this key
                           If False, appends the value if it doesn't exist
        """
        if not key:
            key = self._keyless

        if replace or key not in self._tags:
            self._tags[key] = [value]
            # Invalidate the cache since tags have changed
            self._cached_tag_list = None
        elif value not in self._tags[key]:
            self._tags[key].append(value)
            # Invalidate the cache since tags have changed
            self._cached_tag_list = None

    def set_tags_from_list(self, tag_list: List[str], replace: bool = False) -> None:
        """
        Set multiple tags from a list of strings.
        Strings can be in "key:value" format or just "value" format.
        Args:
            tag_list (List[str]): List of tags in "key:value" format or just "value"
            replace (bool): If True, replaces all existing tags with the new tags list
        """
        if replace:
            self._tags.clear()
            self._cached_tag_list = None

        for tag in tag_list:
            if ':' in tag:
                key, value = tag.split(':', 1)
                self.set_tag(key, value)
            else:
                self.set_tag(None, tag)

    def delete_tag(self, key: Optional[str], value: Optional[str] = None) -> bool:
        """
        Delete a tag or specific value for a tag.
        For keyless tags, use None or empty string as the key.
        Args:
            key (str): The tag key to delete, or None/empty for keyless tags
            value (str, optional): If provided, only deletes this specific value for the key.
                                 If None, deletes all values for the key.
        Returns:
            bool: True if something was deleted, False otherwise
        """
        if not key:
            key = self._keyless

        if key not in self._tags:
            return False

        if value is None:
            # Delete the entire key
            del self._tags[key]
            # Invalidate the cache
            self._cached_tag_list = None
            return True
        else:
            # Delete specific value if it exists
            if value in self._tags[key]:
                self._tags[key].remove(value)
                # Clean up empty lists
                if not self._tags[key]:
                    del self._tags[key]
                # Invalidate the cache
                self._cached_tag_list = None
                return True
        return False

    def _generate_tag_strings(self, tags_dict: Dict[Union[str, TagType], List[str]]) -> tuple[str, ...]:
        """
        Generate a tuple of tag strings from a tags dictionary.
        Args:
            tags_dict (Dict[Union[str, TagType], List[str]]): Dictionary of tags to convert to strings
        Returns:
            tuple[str, ...]: Tuple of tag strings
        """
        return tuple(
            value if key == self._keyless else f"{key}:{value}" for key, values in tags_dict.items() for value in values
        )

    def get_tags(self) -> List[str]:
        """
        Get a list of tag strings.
        For key-value tags, returns "key:value" format.
        For keyless tags, returns just the value.
        The returned list is always sorted alphabetically.
        Returns:
            list: Sorted list of tag strings
        """
        # Return cached list if available
        if self._cached_tag_list is not None:
            return list(self._cached_tag_list)

        # Generate and cache regular tags
        self._cached_tag_list = self._generate_tag_strings(self._tags)
        return list(self._cached_tag_list)
