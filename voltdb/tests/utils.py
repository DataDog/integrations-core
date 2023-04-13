# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from subprocess import PIPE, STDOUT, Popen

from datadog_checks.base.utils.common import ensure_bytes
from datadog_checks.base.utils.http import RequestsWrapper
from datadog_checks.dev.errors import SubprocessError
from datadog_checks.dev.structures import LazyFunction
from datadog_checks.voltdb.client import Client
from datadog_checks.voltdb.types import Instance  # noqa: F401

from . import common


class CreateSchema(LazyFunction):
    def __init__(self, compose_file, schema, container_name):
        # type: (str, str, str) -> None
        # See: https://docs.voltdb.com/UsingVoltDB/ChapDesignSchema.php
        command = [
            'docker',
            'exec',
            '-i',
            container_name,
            'sqlcmd',
            '--user=admin',
            '--password=admin',
        ]

        if common.TLS_ENABLED:
            # See: https://docs.voltdb.com/UsingVoltDB/SecuritySSL.php#SecuritySSLCli
            command += ['--ssl=/tmp/certs/localcert.properties']

        self._command = command
        self._schema = schema

    def __call__(self):
        # type: () -> None
        command = self._command
        schema = self._schema

        process = Popen(command, stdin=PIPE, stdout=PIPE, stderr=STDOUT)
        # Simulate manually typing the schema in.
        # Didn't find any other way to pass the schema (eg --query="file /path/to/schema.sql" won't work).
        process.communicate(ensure_bytes(schema))
        process.wait()

        if process.returncode != 0:
            raise SubprocessError('Command: {}\nExit code: {}'.format(command, process.returncode))


class EnsureExpectedMetricsShowUp(LazyFunction):
    """
    Call procedures to ensure that all expected metrics will be reported by VoltDB.
    """

    def __init__(self, instance):
        # type: (Instance) -> None
        http = RequestsWrapper(instance, {})
        self._client = Client(url=instance['url'], http_get=http.get, username='admin', password='admin')

    def __call__(self):
        # type: () -> None
        # Call procedures to make PROCEDURE and PROCEDUREDETAIL metrics show up...
        # Built-in procedure.
        r = self._client.request('Hero.insert', parameters=[0, 'Bits'])
        assert r.status_code == 200
        assert r.json()["status"] == 1
        # Custom procedure.
        r = self._client.request('LookUpHero', parameters=[0])
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == 1
        rows = data["results"][0]["data"]
        assert rows == [[0, "Bits"]]

        # Create a snapshot to make SNAPSHOTSTATUS metrics appear.
        # See: https://docs.voltdb.com/UsingVoltDB/sysprocsave.php
        block_transactions = 0  # We don't really care, but this is required.
        r = self._client.request('@SnapshotSave', parameters=['/tmp/voltdb/backup/', 'heroes', block_transactions])
        assert r.status_code == 200
        assert r.json()["status"] == 1
