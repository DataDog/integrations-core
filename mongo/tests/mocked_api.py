import itertools
import json
import os

from bson import Timestamp, json_util
from mock import MagicMock

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
        else:
            with open(os.path.join(HERE, "fixtures", "indexStats-{}".format(coll_name)), 'r') as f:
                self.aggregate = MagicMock(return_value=json.load(f, object_hook=json_util.object_hook))


class MockedDB(object):
    def __init__(self, db_name, deployment):
        self._db_name = db_name
        self.current_op = lambda: self.command("current_op")
        self._query_count = 0
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
            filename = "custom-query-{}".format(self._query_count)
            self._query_count += 1
        with open(os.path.join(HERE, "fixtures", filename), 'r') as f:
            return json.load(f, object_hook=json_util.object_hook)


class MockedPyMongoClient(object):
    def __init__(self, deployment):
        self.deployment = deployment
        with open(os.path.join(HERE, "fixtures", "server_info"), 'r') as f:
            self.server_info = MagicMock(return_value=json.load(f))
        with open(os.path.join(HERE, "fixtures", "list_database_names"), 'r') as f:
            self.list_database_names = MagicMock(return_value=json.load(f))

    def __getitem__(self, db_name):
        return MockedDB(db_name, self.deployment)
