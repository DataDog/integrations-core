import itertools
import json
import os

from bson import Timestamp, json_util
from mock import MagicMock

from datadog_checks.mongo.api import MongoApi

from .common import HERE


class MockedCollection(object):
    def __init__(self, db_name, coll_name):
        self._coll_name = coll_name
        self._db_name = db_name
        if coll_name in ("oplog.rs", "oplog.$main"):
            with open(os.path.join(HERE, "fixtures", "oplog_rs_options"), 'r') as f:
                self.options = MagicMock(return_value=json.load(f, object_hook=json_util.object_hook))

            val1 = [{'ts': Timestamp(1600262019, 1)}]
            val2 = [{'ts': Timestamp(1600327624, 8)}]
            limit = MagicMock(limit=MagicMock(side_effect=itertools.cycle([val1, val2])))
            sort = MagicMock(sort=MagicMock(return_value=limit))
            self.find = MagicMock(return_value=sort)
        elif coll_name == 'system.sessions':
            with open(os.path.join(HERE, "fixtures", "system.sessions"), 'r') as f:
                content = json.load(f, object_hook=json_util.object_hook)
                self.aggregate = MagicMock(return_value=iter([content]))
        elif coll_name == 'chunks':
            self.count_documents = MagicMock(side_effect=[100, 5])
        else:
            with open(os.path.join(HERE, "fixtures", "indexStats-{}".format(coll_name)), 'r') as f:
                self.aggregate = MagicMock(return_value=json.load(f, object_hook=json_util.object_hook))


class MockedDB(object):
    def __init__(self, db_name, deployment):
        self._db_name = db_name
        self.current_op = lambda: self.command("current_op")
        self.deployment = deployment

    def __getitem__(self, coll_name):
        return MockedCollection(self._db_name, coll_name)

    def authenticate(self, *_, **__):
        return True

    def command(self, command, *args, **_):
        filename = command
        if command == "dbstats":
            filename += "-{}".format(self._db_name)
        elif command == "collstats":
            coll_name = args[0]
            filename += "-{}".format(coll_name)
        elif command in ("getCmdLineOpts", "replSetGetStatus"):
            filename += "-{}".format(self.deployment)
        elif command in ("find", "count", "aggregate"):
            # At time of writing, those commands only are for custom queries.
            filename = "custom-query-{}".format(command)
        with open(os.path.join(HERE, "fixtures", filename), 'r') as f:
            return json.load(f, object_hook=json_util.object_hook)


class MockedPyMongoClient(MongoApi):
    def __init__(self, config, log, deployment, replicaset=None):
        self._config = config
        self._log = log
        self._replicaset = replicaset
        self.deployment_type = None
        self.deployment = deployment
        with open(os.path.join(HERE, "fixtures", "server_info"), 'r') as f:
            self.server_info = MagicMock(return_value=json.load(f))
        with open(os.path.join(HERE, "fixtures", "list_database_names"), 'r') as f:
            self.list_database_names = MagicMock(return_value=json.load(f))

        self.db_cache = {}
        MongoApi._initialize(self)

    def __getitem__(self, db_name):
        if db_name not in self.db_cache:
            self.db_cache[db_name] = MockedDB(db_name, self.deployment)

        return self.db_cache[db_name]

    def _authenticate(self):
        return MongoApi._authenticate(self)

    def _get_deployment_type(self):
        return MongoApi._get_deployment_type(self)
