import concurrent.futures
import contextlib
import datetime
import random
import threading
from concurrent.futures.thread import ThreadPoolExecutor
from typing import Callable, Dict

import psycopg
import time
from psycopg import ClientCursor
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class ReproduceError(object):

    def __init__(self):
        self.db_pool = MultiDatabaseConnectionPool(self._new_connection, 30)
        self.db = None
        self._check_cancelled = False
        self.job_one = Job(self.test_query, job_name="job-one")
        self.job_two = Job(self.test_query, job_name="job-two")
        self.job_three = Job(self.test_query, job_name="job-three")

    def test_query(self, job_name):
        queries = [
            "INSERT INTO breed (name) VALUES ('Golden Retriever');",
            "INSERT INTO breed (name) VALUES ('GOOBY');",
            "INSERT INTO breed (name) VALUES ('Good Boy');",
            "SELECT * FROM kennel WHERE address LIKE '%New%';",
            "SELECT * FROM kennel WHERE address LIKE '%Y%';",
            "SELECT pg_sleep(3);"
        ]
        random_query = random.choice(queries)
        with self.db_pool.get_main_db().connection() as conn:
            with conn.cursor(row_factory=dict_row) as cursor:
                cursor.execute(random_query)
        if job_name == "job-three":
            # mock query-samples thread, which requires the connection pooling across dbs
            try:
                # print("{}".format(self.db_pool.get_connection("dogs", 100).get_stats()))
                with self.db_pool.get_connection("dogs", 60000).connection() as conn:
                    print("running query test_query func {}".format(random_query))
                    with conn.cursor() as cursor:
                        cursor.execute(random_query)
            finally:
                self.db_pool.set_pool_inactive("dogs")
            self.db_pool.prune_connections()

    def _close_db_pool(self):
        self.db_pool.close_all_connections(timeout=5)

    def cancel(self):
        """
        Cancels and waits for all threads to stop, and then
        closes any open db connections
        """
        with concurrent.futures.ThreadPoolExecutor() as executor:
            tasks = [
                executor.submit(thread.cancel)
                for thread in [self.job_one, self.job_two, self.job_three]
            ]

            try:
                concurrent.futures.wait(tasks, timeout=5)
            except concurrent.futures.TimeoutError:
                print(
                    "Not all job loops were completed in time when cancelling the main check. "
                    "Proceeding with the check cancellation. "
                    "Some unexpected errors related to closed connections may occur after this message."
                )
        print("shutting down all pool connections")
        self._close_db_pool()
        self._check_cancelled = True

    def run(self):
        try:
            self._connect("dogs")
            self.job_one.run_job_loop()
            self.job_two.run_job_loop()
            self.job_three.run_job_loop()
            with self.db.connection() as conn:
                with conn.cursor() as cursor:
                    print("running query from main loop")
                    cursor.execute("Select pg_sleep(3);")
        except Exception as e:
            print("exception thrown in main loop {}".format(e))
            self.db = None
            raise e
        finally:
            if self._check_cancelled and self.db:
                try:
                    # once check finishes on a cancel, shut down main connection gracefully
                    self.db.close()
                except Exception:
                    print("failed to close DB connection for db={}".format("dogs"))

    def _connect(self, dbname):
        """
        Set the connection for main check thread.
        This is to be managed outside the
        db connection pool, so on cancel it
        can be properly closed after the check completes
        """
        if self.db and self.db.closed:
            # Reset the connection object to retry to connect
            self.db = None
        # if self.db:
        #     if self.db.info.status != psycopg.pq.ConnStatus.OK:
        #         # Some transaction went wrong and the connection is in an unhealthy state. Let's fix that
        #         self.db.rollback()
        # else:
        self.db = self._new_connection(dbname)

    # def _new_connection(self, dbname):
    #     connection_string = "host=localhost user=postgres dbname={} application_name=my-app password=datad0g".format(
    #         dbname)
    #     connection_string += " options='-c statement_timeout=%s'" % 5000
    #     conn = psycopg.connect(conninfo=connection_string, autocommit=True, cursor_factory=ClientCursor)
    #     return conn

    def _new_connection(self, dbname):
        connection_string = "host=localhost user=postgres dbname={} application_name=my-app password=datad0g".format(dbname)
        kwargs = {
            "options": "-c statement_timeout=%s" % 5000
        }
        pool = ConnectionPool(conninfo=connection_string, min_size=1, kwargs=kwargs, open=True, name=dbname)
        return pool


class Job(object):
    executor = ThreadPoolExecutor(100000)

    def __init__(self, run_func, rate_limit=2, job_name=None):
        self._job_loop_future = None
        self._cancel_event = threading.Event()
        self.rate_limit = rate_limit
        self.job_name = job_name
        self._rate_limiter = ConstantRateLimiter(rate_limit)
        self._run_func = run_func

    def run_job_loop(self):
        print("starting up job loop {}".format(self.job_name))
        if self._job_loop_future is None or not self._job_loop_future.running():
            self._job_loop_future = Job.executor.submit(self._job_loop)

    def cancel(self):
        """
        Send a signal to cancel the job loop asynchronously.
        """
        self._cancel_event.set()
        # after setting cancel event, wait for job loop to fully shutdown
        while self._job_loop_future.running():
            time.sleep(0.1)

    def _job_loop(self):
        try:
            while True:
                if self._cancel_event.isSet():
                    print("[{}] Job loop cancelled".format(self.job_name))
                    break
                self._run_job_rate_limited()
        except Exception as e:
            if self._cancel_event.isSet():
                print("exception thrown after {} cancel {}".format(self.job_name, e))
            else:
                print("exception thrown during {} loop {}".format(self.job_name, e))

    def _run_job_rate_limited(self):
        self._run_func(self.job_name)
        if not self._cancel_event.isSet():
            self._rate_limiter.sleep()


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


class ConnectionPoolFullError(Exception):
    def __init__(self, size, timeout):
        self.size = size
        self.timeout = timeout

    def __str__(self):
        return "Could not insert connection in pool size {} within {} seconds".format(self.size, self.timeout)


class ConnectionInfo:
    def __init__(
            self,
            connection: psycopg.Connection,
            deadline: int,
            active: bool,
            last_accessed: int,
            persistent: bool,
    ):
        self.connection = connection
        self.deadline = deadline
        self.active = active
        self.last_accessed = last_accessed
        self.persistent = persistent


class MultiDatabaseConnectionPool(object):
    """
    Manages a connection pool across many logical databases with a maximum of 1 conn per
    database. Traditional connection pools manage a set of connections to a single database,
    however the usage patterns of the Agent application should aim to have minimal footprint
    and reuse a single connection as much as possible.

    Even when limited to a single connection per database, an instance with hundreds of
    databases still present a connection overhead risk. This class provides a mechanism
    to prune connections to a database which were not used in the time specified by their
    TTL.

    If max_conns is specified, the connection pool will limit concurrent connections.
    """

    class Stats(object):
        def __init__(self):
            self.connection_opened = 0
            self.connection_pruned = 0
            self.connection_closed = 0
            self.connection_closed_failed = 0

        def __repr__(self):
            return str(self.__dict__)

        def reset(self):
            self.__init__()

    def __init__(self, connect_fn: Callable[[str], None], max_conns: int = None, main_conn_pool_size: int = 3):
        self.max_conns: int = max_conns
        self._stats = self.Stats()
        self._mu = threading.RLock()
        self._conns: Dict[str, ConnectionInfo] = {}
        self.connect_fn = connect_fn
        # use psycopg_pool module to manage persistent db connections
        # to the main database, typically this is the `postgres` db
        self.main_db_conn = None
        self.min_conn_pool_size = main_conn_pool_size

    def _get_main_conn_pool(self, min_size: int, timeout: int = None):
        connection_string = "host=localhost user=postgres dbname=dogs application_name=my-app password=datad0g"
        kwargs = {
            "options": "-c statement_timeout=%s" % 5000
        }
        pool = ConnectionPool(conninfo=connection_string, min_size=min_size, kwargs=kwargs, open=True, name="dogs")
        print("grabbed new connection pool")
        return pool

    def _get_connection_raw(
            self,
            dbname: str,
            ttl_ms: int,
            conn_prefix: str = None,
            timeout: int = None,
            startup_fn: Callable[[psycopg.Connection], None] = None,
            persistent: bool = False,
    ) -> psycopg.Connection:
        """
        Return a connection from the pool.
        Pass a function to startup_func if there is an action needed with the connection
        when re-establishing it.
        """
        start = datetime.datetime.now()
        self.prune_connections()
        conn_name = dbname
        if conn_prefix:
            conn_name = "{}-{}".format(conn_prefix, dbname)
        with self._mu:
            conn = self._conns.pop(conn_name, ConnectionInfo(None, None, None, None, None))
            db = conn.connection
            if db is None or db.closed:
                if self.max_conns is not None:
                    # try to free space until we succeed
                    while len(self._conns) >= self.max_conns:
                        self.prune_connections()
                        self.evict_lru()
                        if timeout is not None and (datetime.datetime.now() - start).total_seconds() > timeout:
                            raise ConnectionPoolFullError(self.max_conns, timeout)
                        time.sleep(0.01)
                        continue
                self._stats.connection_opened += 1
                db = self.connect_fn(dbname)
                if startup_fn:
                    startup_fn(db)
            else:
                # if already in pool, retain persistence status
                persistent = conn.persistent

            # if db.info.status != psycopg.pq.ConnStatus.OK:
            #     # Some transaction went wrong and the connection is in an unhealthy state. Let's fix that
            #     db.rollback()

            deadline = datetime.datetime.now() + datetime.timedelta(milliseconds=ttl_ms)
            self._conns[conn_name] = ConnectionInfo(
                connection=db,
                deadline=deadline,
                active=True,
                last_accessed=datetime.datetime.now(),
                persistent=persistent,
            )
            return db

    def get_connection(
            self, dbname: str, ttl_ms: int, conn_prefix: str = None, timeout: int = None, persistent: bool = False
    ):
        """
        Grab a connection from the pool if the database is already connected.
        If max_conns is specified, and the database isn't already connected,
        make a new connection if the max_conn limit hasn't been reached.
        Blocks until a connection can be added to the pool,
        and optionally takes a timeout in seconds.
        """
        with self._mu:
            db = self._get_connection_raw(
                dbname=dbname, ttl_ms=ttl_ms, conn_prefix=conn_prefix, timeout=timeout, persistent=persistent
            )
            return db

    def set_pool_inactive(self, conn_name):
        with self._mu:
            try:
                self._conns[conn_name].active = False
            except KeyError:
                # if self._get_connection_raw hit an exception, self._conns[conn_name] didn't get populated
                pass

    def prune_connections(self):
        """
        This function should be called periodically to prune all connections which have not been
        accessed since their TTL. This means that connections which are actually active on the
        server can still be closed with this function. For instance, if a connection is opened with
        ttl 1000ms, but the query it's running takes 5000ms, this function will still try to close
        the connection mid-query.
        """
        with self._mu:
            now = datetime.datetime.now()
            for conn_name, conn in list(self._conns.items()):
                if conn.deadline < now and not conn.active:
                    self._stats.connection_pruned += 1
                    self._terminate_connection_unsafe(conn_name)

    def close_all_connections(self, timeout=None):
        """
        Will block until all connections are terminated, unless the pre-configured timeout is hit
        :param timeout:
        :return:
        """
        success = True
        start_time = time.time()
        with self._mu:
            while self._conns and (timeout is None or time.time() - start_time < timeout):
                dbname = next(iter(self._conns))
                if not self._terminate_connection_unsafe(dbname):
                    success = False
        try:
            print("closing db pool connections")
            if self.main_db_conn and not self.main_db_conn.closed:
                self.main_db_conn.close(timeout=5)
        except Exception as e:
            print(e)
            success = False
        return success

    def evict_lru(self) -> str:
        """
        Evict and close the inactive connection which was least recently used.
        Return the dbname connection that was evicted or None if we couldn't evict a connection.
        """
        with self._mu:
            sorted_conns = sorted(self._conns.items(), key=lambda i: i[1].last_accessed)
            for name, conn_info in sorted_conns:
                if not conn_info.active and not conn_info.persistent:
                    self._terminate_connection_unsafe(name)
                    return name

            # Could not evict a candidate; return None
            return None

    def _terminate_connection_unsafe(self, conn_name: str):
        db = self._conns.pop(conn_name, ConnectionInfo(None, None, None, None, None))
        if db is not None:
            try:
                # close connection pool
                if not db.connection.closed:
                    print("closing conn pool")
                    db.connection.close()
                self._stats.connection_closed += 1
            except Exception:
                self._stats.connection_closed_failed += 1
                print("failed to close DB connection for db=%s", conn_name)
                return False
        return True

    def get_main_db(self, timeout: int = None):
        if self.main_db_conn is None or self.main_db_conn.closed:
            self.main_db_conn = self._get_main_conn_pool(self.min_conn_pool_size, timeout)
        # print("main db stats {}".format(self.main_db_conn.get_stats()))
        return self.main_db_conn


def run_loop(fun_times):
    while True:
        fun_times.run()
        time.sleep(1)


def random_cancel(fun_times):
    time.sleep(random.randint(60, 600))
    fun_times.cancel()


if __name__ == "__main__":
    while True:
        fun_times = ReproduceError()

        thread_run = threading.Thread(target=run_loop, args=(fun_times,))
        thread_cancel = threading.Thread(target=random_cancel, args=(fun_times,))

        thread_run.start()
        thread_cancel.start()

        thread_cancel.join()
        # thread_run.join()
        print("ended loop, re-running")
        time.sleep(1)
