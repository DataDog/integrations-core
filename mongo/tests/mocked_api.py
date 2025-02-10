# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import itertools
import json
import os

from bson import Timestamp, json_util
from mock import MagicMock

from .common import HERE


class MockedCollection(object):
    def __init__(self, db_name, coll_name, deployment):
        self._coll_name = coll_name
        self._db_name = db_name
        self.deployment = deployment
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
        elif coll_name == 'system.replset':
            with open(os.path.join(HERE, "fixtures", "system.replset"), 'r') as f:
                content = json.load(f, object_hook=json_util.object_hook)
                self.find_one = MagicMock(return_value=content)
        elif coll_name == 'system.profile':
            with open(os.path.join(HERE, "fixtures", "system.profile"), 'r') as f:
                content = json.load(f, object_hook=json_util.object_hook)

                def mocked_sort(*args, **kwargs):
                    return content

                self.find = MagicMock(return_value=MagicMock(sort=mocked_sort))
        elif db_name == "config" and coll_name == "collections":
            with open(os.path.join(HERE, "fixtures", f"config-collections-{self.deployment}"), 'r') as f:
                self.find_one = MagicMock(return_value=json.load(f, object_hook=json_util.object_hook))

    def index_information(self, session=None, **kwargs):
        with open(os.path.join(HERE, "fixtures", "index_information"), 'r') as f:
            return json.load(f, object_hook=json_util.object_hook)

    def list_search_indexes(self, session=None, **kwargs):
        with open(os.path.join(HERE, "fixtures", "list_search_indexes"), 'r') as f:
            return json.load(f, object_hook=json_util.object_hook)

    def aggregate(self, pipeline, session=None, **kwargs):
        if '$indexStats' in pipeline[0]:
            with open(os.path.join(HERE, "fixtures", f"$indexStats-{self._coll_name}"), 'r') as f:
                return iter(json.load(f, object_hook=json_util.object_hook))
        elif '$collStats' in pipeline[0]:
            with open(os.path.join(HERE, "fixtures", f"$collStats-{self._coll_name}"), 'r') as f:
                return iter(json.load(f, object_hook=json_util.object_hook))
        elif '$sample' in pipeline[0]:
            with open(os.path.join(HERE, "fixtures", f"$sample-{self._coll_name}"), 'r') as f:
                return iter(json.load(f, object_hook=json_util.object_hook))


class MockedDB(object):
    def __init__(self, db_name, deployment):
        self._db_name = db_name
        self.deployment = deployment

    def __getitem__(self, coll_name):
        return MockedCollection(self._db_name, coll_name, self.deployment)

    def command(self, command, *args, **kwargs):
        filename = command
        if "dbStats" in command:
            filename = f"dbstats-{self._db_name}"
        elif command == "collstats":
            coll_name = args[0]
            filename += f"-{coll_name}"
        elif command in ("getCmdLineOpts", "replSetGetStatus", "isMaster"):
            filename += f"-{self.deployment}"
        elif command in ("find", "count", "aggregate"):
            # At time of writing, those commands only are for custom queries.
            filename = f"custom-query-{command}"
        elif command == "explain":
            filename = f"explain-{self.deployment}"
        elif command == "profile":
            filename = f"profile-{self._db_name}"
        elif command == "getLog":
            filename = f"getLog-{self.deployment}"
        with open(os.path.join(HERE, "fixtures", filename), 'r') as f:
            return json.load(f, object_hook=json_util.object_hook)

    def list_collection_names(self, session=None, filter=None, comment=None, **kwargs):
        filename = f"list_collection_names-{self._db_name}"
        if not os.path.exists(os.path.join(HERE, "fixtures", filename)):
            filename = "list_collection_names"
        with open(os.path.join(HERE, "fixtures", filename), 'r') as f:
            return json.load(f)

    def aggregate(self, pipeline, session=None, **kwargs):
        if pipeline[0] == {'$currentOp': {'allUsers': True}}:
            # mock the $currentOp aggregation used for operation sampling
            with open(os.path.join(HERE, "fixtures", f"$currentOp-{self.deployment}"), 'r') as f:
                return iter(json.load(f, object_hook=json_util.object_hook))
        elif pipeline[0] == {"$shardedDataDistribution": {}}:
            with open(os.path.join(HERE, "fixtures", "$shardedDataDistribution"), 'r') as f:
                return iter(json.load(f, object_hook=json_util.object_hook))
        return []


class MockedPyMongoClient(object):
    def __init__(self, deployment):
        self.deployment = deployment
        with open(os.path.join(HERE, "fixtures", "server_info"), 'r') as f:
            self.server_info = MagicMock(return_value=json.load(f))
        with open(os.path.join(HERE, "fixtures", "list_database_names"), 'r') as f:
            self.list_database_names = MagicMock(return_value=json.load(f))

        self.db_cache = {}

    def __getitem__(self, db_name):
        if db_name not in self.db_cache:
            self.db_cache[db_name] = MockedDB(db_name, self.deployment)

        return self.db_cache[db_name]
