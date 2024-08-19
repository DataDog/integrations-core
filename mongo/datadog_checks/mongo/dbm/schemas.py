# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import datetime
import time
from collections import defaultdict

from bson import json_util

from datadog_checks.mongo.dbm.utils import MONGODB_SYSTEM_DATABASES

try:
    import datadog_agent
except ImportError:
    from datadog_checks.base.stubs import datadog_agent

from datadog_checks.base.utils.db.utils import DBMAsyncJob
from datadog_checks.base.utils.tracking import tracked_method


def agent_check_getter(self):
    return self._check


class MongoSchemas(DBMAsyncJob):
    def __init__(self, check):
        self._schemas_config = check._config.schemas
        self._collection_interval = self._schemas_config["collection_interval"]
        self._max_collections = self._schemas_config["max_collections"]
        self._sample_size = self._schemas_config["sample_size"]

        super(MongoSchemas, self).__init__(
            check,
            rate_limit=1 / self._collection_interval,
            run_sync=self._schemas_config.get("run_sync", True),  # Default to sync mode
            enabled=self._schemas_config["enabled"],
            dbms="mongo",
            min_collection_interval=check._config.min_collection_interval,
            job_name="schemas",
        )

    def run_job(self):
        self.collect_schemas()

    @tracked_method(agent_check_getter=agent_check_getter)
    def collect_schemas(self):
        if not self._should_collect_schemas():
            self._check.log.debug(
                "Skipping schema collection. Schema collection only runs on ReplicaSet primary or Mongos."
            )
            return

        collected_collections = 0
        databases = []
        for db_name in self._check._database_autodiscovery.databases:
            if db_name in MONGODB_SYSTEM_DATABASES:
                self._check.log.debug("Skipping system database %s", db_name)
                continue
            if collected_collections >= self._max_collections:
                break

            collections = []
            for coll_name in self._check.api_client.list_authorized_collections(db_name):
                collection = self._discover_collection(db_name, coll_name)
                collections.append(collection)
                collected_collections += 1
                if collected_collections >= self._max_collections:
                    self._check.log.debug("Reached max collections limit %d", self._max_collections)
                    break
            databases.append(
                {
                    "name": db_name,
                    "collections": collections,
                }
            )

        self._submit_schema_payload(databases)

    def _should_collect_schemas(self) -> bool:
        # Only collect schemas on primary or mongos
        return self._check.deployment_type.is_principal()

    def _discover_collection(self, dbname, collname):
        schema = self._discover_collection_schema(dbname, collname)
        indexes = self._discover_collection_indexes(dbname, collname)
        return {
            "name": collname,
            "namespace": f"{dbname}.{collname}",
            "docs": schema,
            "indexes": indexes,
        }

    def _discover_collection_schema(self, dbname, collname):
        # Sample the collection, fetch sampled docs into memory
        # so that we know the length of sampled docs in case it's less than the sample size
        sampled_docs = list(self._check.api_client.sample(dbname, collname, self._sample_size))
        if len(sampled_docs) < self._sample_size:
            self._check.log.debug(
                "Sampled documents count is less than the sample size for %s.%s, ",
                "sampled %d documents instead of %d",
                dbname,
                collname,
                len(sampled_docs),
                self._sample_size,
            )

        schema_types = defaultdict(set)
        field_prevalence = defaultdict(int)
        for doc in sampled_docs:
            doc_structure, field_prevalence = self._analyze_doc_structure(
                doc, "", field_prevalence, scale=len(sampled_docs)
            )
            for key, types in doc_structure.items():
                schema_types[key].update(types)

        return [
            {
                "name": key,
                "types": sorted(types),
                "prevalence": field_prevalence[key],
            }
            for key, types in schema_types.items()
        ]

    def _discover_collection_indexes(self, dbname, collname):
        indexes = self._check.api_client.index_information(dbname, collname)
        return [
            {
                "name": index_name,
                "keys": [
                    {
                        "field": field,
                        "type": str(index_type),
                    }
                    for field, index_type in index.get("key", [])
                ],
            }
            for index_name, index in indexes.items()
        ]

    def _submit_schema_payload(self, database_schemas):
        payload = {
            "host": self._check._resolved_hostname,
            "agent_version": datadog_agent.get_version(),
            "dbms": "mongo",
            "kind": "mongodb_databases",
            "collection_interval": self._collection_interval,
            "dbms_version": self._check._mongo_version,
            "tags": self._check._get_tags(include_deployment_tags=True),
            "timestamp": time.time() * 1000,
            "metadata": database_schemas,
        }
        json_payload = json_util.dumps(payload)
        self._check.log.debug("Submitting schema payload: %s", json_payload)
        self._check.database_monitoring_metadata(json_payload)

    def _analyze_doc_structure(self, document, path, field_prevalence, scale):
        '''
        Function to analyze the structure of a document and return the field types and counts
        '''
        structure = defaultdict(set)
        for key, value in document.items():
            full_path = f"{path}.{key}" if path else key
            value_type = self._determine_value_type(value)
            structure[full_path].add(value_type)

            if isinstance(value, dict):
                nested_structure, field_prevalence = self._analyze_doc_structure(
                    value, full_path, field_prevalence, scale=scale
                )
                for nested_key, nested_types in nested_structure.items():
                    structure[nested_key].update(nested_types)
                field_prevalence[full_path] += 1 / scale
            elif isinstance(value, list):
                # Count the array field once per document
                field_prevalence[full_path] += 1 / scale
                for item in value:
                    if isinstance(item, dict):
                        nested_structure, field_prevalence = self._analyze_doc_structure(
                            item, full_path, field_prevalence, scale=len(value) * scale
                        )
                        for nested_key, nested_types in nested_structure.items():
                            structure[nested_key].update(nested_types)
            else:
                field_prevalence[full_path] += 1 / scale

        return structure, field_prevalence

    def _determine_value_type(self, value):
        if isinstance(value, str):
            return "String"
        elif isinstance(value, int):
            return "Int32"
        elif isinstance(value, float):
            return "Double"
        elif isinstance(value, bool):
            return "Boolean"
        elif isinstance(value, list):
            return "Array"
        elif isinstance(value, dict):
            return "Object"
        elif isinstance(value, datetime.datetime):
            return "Date"
        elif value is None:
            return "Null"
        else:
            return type(value).__name__
