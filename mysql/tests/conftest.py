# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import logging
import os

import mock
import pymysql
import pytest
from datadog_checks.dev import TempDir, WaitFor, docker_run
from datadog_checks.dev.conditions import CheckDockerLogs

from . import common, tags

logger = logging.getLogger(__name__)

MYSQL_FLAVOR = os.getenv('MYSQL_FLAVOR')
MYSQL_VERSION = os.getenv('MYSQL_VERSION')
COMPOSE_FILE = os.getenv('COMPOSE_FILE')


@pytest.fixture(scope='session')
def config_e2e():
    logs_path = _mysql_logs_path()

    return {
        'init_config': {},
        'instances': [{'host': common.HOST, 'user': common.USER, 'pass': common.PASS, 'port': common.PORT}],
        'logs': [
            {'type': 'file', 'path': '{}/mysql.log'.format(logs_path), 'source': 'mysql', 'service': 'local_mysql'},
            {
                'type': 'file',
                'path': '{}/mysql_slow.log'.format(logs_path),
                'source': 'mysql',
                'service': 'local_mysql',
                'log_processing_rules': [
                    {'type': 'multi_line', 'name': 'log_starts_with_time', 'pattern': '# Time: '},
                ],
            },
        ],
    }


@pytest.fixture(scope='session')
def dd_environment(config_e2e):
    logs_path = _mysql_logs_path()

    with TempDir('logs') as logs_host_path:
        e2e_metadata = {'docker_volumes': ['{}:{}'.format(logs_host_path, logs_path)]}

        with docker_run(
            os.path.join(common.HERE, 'compose', COMPOSE_FILE),
            env_vars={
                'MYSQL_DOCKER_REPO': _mysql_docker_repo(),
                'MYSQL_PORT': str(common.PORT),
                'MYSQL_SLAVE_PORT': str(common.SLAVE_PORT),
                'MYSQL_CONF_PATH': _mysql_conf_path(),
                'MYSQL_LOGS_HOST_PATH': logs_host_path,
                'MYSQL_LOGS_PATH': logs_path,
                'WAIT_FOR_IT_SCRIPT_PATH': _wait_for_it_script(),
            },
            conditions=[
                WaitFor(init_master, wait=2),
                WaitFor(init_slave, wait=2),
                CheckDockerLogs('mysql-slave', ["ready for connections", "mariadb successfully initialized"]),
                populate_database,
            ],
        ):
            yield config_e2e, e2e_metadata


@pytest.fixture(scope='session')
def instance_basic(config_e2e):
    return config_e2e['instances'][0]


@pytest.fixture
def instance_complex():
    return {
        'host': common.HOST,
        'user': common.USER,
        'pass': common.PASS,
        'port': common.PORT,
        'options': {
            'replication': True,
            'extra_status_metrics': True,
            'extra_innodb_metrics': True,
            'extra_performance_metrics': True,
            'schema_size_metrics': True,
        },
        'tags': tags.METRIC_TAGS,
        'queries': [
            {
                'query': "SELECT * from testdb.users where name='Alice' limit 1;",
                'metric': 'alice.age',
                'type': 'gauge',
                'field': 'age',
            },
            {
                'query': "SELECT * from testdb.users where name='Bob' limit 1;",
                'metric': 'bob.age',
                'type': 'gauge',
                'field': 'age',
            },
        ],
    }


@pytest.fixture
def instance_custom_queries():
    return {
        'host': common.HOST,
        'user': common.USER,
        'pass': common.PASS,
        'port': common.PORT,
        'tags': tags.METRIC_TAGS,
        'custom_queries': [
            {
                'query': "SELECT * from testdb.users where name='Alice' limit 1;",
                'columns': [{}, {'name': 'alice.age', 'type': 'gauge'}],
            },
            {
                'query': "SELECT * from testdb.users where name='Bob' limit 1;",
                'columns': [{}, {'name': 'bob.age', 'type': 'gauge'}],
            },
        ],
    }


@pytest.fixture(scope='session')
def instance_error():
    return {'host': common.HOST, 'user': 'unknown', 'pass': common.PASS}


@pytest.fixture(scope='session')
def version_metadata():
    parts = MYSQL_VERSION.split('-')
    version = parts[0].split('.')
    major, minor = version[:2]
    patch = version[2] if len(version) > 2 else mock.ANY

    flavor = "MariaDB" if MYSQL_FLAVOR == "mariadb" else "MySQL"

    return {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': mock.ANY,
        'version.build': mock.ANY,
        'flavor': flavor,
    }


def _init_datadog_sample_collection(conn):
    logger.debug("initializing datadog sample collection")
    cur = conn.cursor()
    cur.execute("CREATE DATABASE datadog")
    cur.execute("GRANT CREATE TEMPORARY TABLES ON `datadog`.* TO 'dog'@'%'")
    _create_explain_procedure(conn, "datadog")
    _create_explain_procedure(conn, "mysql")
    _create_enable_consumers_procedure(conn)


def _create_explain_procedure(conn, schema):
    logger.debug("creating explain procedure in schema=%s", schema)
    cur = conn.cursor()
    cur.execute(
        """
    CREATE PROCEDURE {schema}.explain_statement(IN query TEXT)
        SQL SECURITY DEFINER
    BEGIN
        SET @explain := CONCAT('EXPLAIN FORMAT=json ', query);
        PREPARE stmt FROM @explain;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END;
    """.format(
            schema=schema
        )
    )
    cur.execute("GRANT EXECUTE ON PROCEDURE {schema}.explain_statement to 'dog'@'%'".format(schema=schema))
    cur.close()


def _create_enable_consumers_procedure(conn):
    logger.debug("creating enable_events_statements_consumers procedure")
    cur = conn.cursor()
    cur.execute("""
        CREATE PROCEDURE datadog.enable_events_statements_consumers()
            SQL SECURITY DEFINER
        BEGIN
            UPDATE performance_schema.setup_consumers SET enabled='YES' WHERE name LIKE 'events_statements_%';
        END;
    """)
    cur.execute("GRANT EXECUTE ON PROCEDURE datadog.enable_events_statements_consumers to 'dog'@'%'")
    cur.close()


def init_master():
    logger.debug("initializing master")
    conn = pymysql.connect(host=common.HOST, port=common.PORT, user='root')
    _add_dog_user(conn)
    _add_bob_user(conn)
    _init_datadog_sample_collection(conn)


@pytest.fixture
def root_conn():
    conn = pymysql.connect(host=common.HOST, port=common.PORT, user='root')
    yield conn
    conn.close()


def init_slave():
    logger.debug("initializing slave")
    pymysql.connect(host=common.HOST, port=common.SLAVE_PORT, user=common.USER, passwd=common.PASS)


def _add_dog_user(conn):
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM mysql.user WHERE User = 'dog' and Host = '%'")
    if cur.fetchone()[0] == 0:
        # gracefully handle retries due to partial failure later on
        cur.execute("CREATE USER 'dog'@'%' IDENTIFIED BY 'dog'")
    cur.execute("GRANT PROCESS ON *.* TO 'dog'@'%'")
    cur.execute("GRANT REPLICATION CLIENT ON *.* TO 'dog'@'%'")
    cur.execute("GRANT SELECT ON performance_schema.* TO 'dog'@'%'")
    if MYSQL_FLAVOR == 'mysql' and MYSQL_VERSION == '8.0':
        cur.execute("ALTER USER 'dog'@'%' WITH MAX_USER_CONNECTIONS 0")
    else:
        cur.execute("UPDATE mysql.user SET max_user_connections = 0 WHERE user='dog' AND host='%'")
        cur.execute("FLUSH PRIVILEGES")


def _add_bob_user(conn):
    cur = conn.cursor()
    cur.execute("CREATE USER 'bob'@'%' IDENTIFIED BY 'bob'")
    cur.execute("GRANT USAGE on *.* to 'bob'@'%'")


@pytest.fixture
def bob_conn():
    conn = pymysql.connect(host=common.HOST, port=common.PORT, user='bob', password='bob')
    yield conn
    conn.close()


def populate_database():
    logger.debug("populating database")
    conn = pymysql.connect(host=common.HOST, port=common.PORT, user='root')

    cur = conn.cursor()

    cur.execute("USE mysql;")
    cur.execute("CREATE DATABASE testdb;")
    cur.execute("USE testdb;")
    cur.execute("CREATE TABLE testdb.users (name VARCHAR(20), age INT);")
    cur.execute("INSERT INTO testdb.users (name,age) VALUES('Alice',25);")
    cur.execute("INSERT INTO testdb.users (name,age) VALUES('Bob',20);")
    cur.execute("GRANT SELECT ON testdb.users TO 'dog'@'%';")
    cur.execute("GRANT SELECT ON testdb.users TO 'bob'@'%';")
    cur.close()
    _create_explain_procedure(conn, "testdb")


def _wait_for_it_script():
    """
    FIXME: relying on the filesystem layout is a bad idea, the testing helper
    should expose its path through the api instead
    """
    script = os.path.join(common.TESTS_HELPER_DIR, 'scripts', 'wait-for-it.sh')
    return os.path.abspath(script)


def _mysql_conf_path():
    """
    Return the path to a local MySQL configuration file suited for the current environment.
    """
    if MYSQL_FLAVOR == 'mysql':
        filename = 'mysql.conf'
    elif MYSQL_FLAVOR == 'mariadb':
        filename = 'mariadb.conf'
    else:
        raise ValueError('Unsupported MySQL flavor: {}'.format(MYSQL_FLAVOR))

    conf = os.path.join(common.HERE, 'compose', filename)
    return os.path.abspath(conf)


def _mysql_logs_path():
    """
    Return the path to the MySQL logs directory in the MySQL container.

    Should be kept in sync with the log paths set in the local MySQL configuration files
    (which don't support interpolation of environment variables).
    """
    if MYSQL_FLAVOR == 'mysql':
        if MYSQL_VERSION == '8.0':
            return '/opt/bitnami/mysql/logs'
        else:
            return '/var/log/mysql'
    elif MYSQL_FLAVOR == 'mariadb':
        return '/opt/bitnami/mariadb/logs'
    else:
        raise ValueError('Unsupported MySQL flavor: {}'.format(MYSQL_FLAVOR))


def _mysql_docker_repo():
    if MYSQL_FLAVOR == 'mysql':
        # The image for testing Mysql 5.5 is located at `jfullaondo/mysql-replication` or `bergerx/mysql-replication`
        # Warning: This image is a bit flaky on CI (it has been removed
        # https://github.com/DataDog/integrations-core/pull/4669)
        if MYSQL_VERSION in ('5.6', '5.7'):
            return 'bergerx/mysql-replication'
        elif MYSQL_VERSION == '8.0':
            return 'bitnami/mysql'
    elif MYSQL_FLAVOR == 'mariadb':
        return 'bitnami/mariadb'
    else:
        raise ValueError('Unsupported MySQL flavor: {}'.format(MYSQL_FLAVOR))
