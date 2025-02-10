# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


import datetime
import time
from collections import defaultdict

from bson import json_util

from datadog_checks.mongo.common import HostingType
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
        self._max_depth = self._schemas_config["max_depth"]
        self._collect_search_indexes = self._schemas_config["collect_search_indexes"]
        self._max_collections_per_database = check._config.database_autodiscovery_config['max_collections_per_database']

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

        base_payload = {
            "host": self._check._resolved_hostname,
            "agent_version": datadog_agent.get_version(),
            "dbms": "mongo",
            "kind": "mongodb_databases",
            "collection_interval": self._collection_interval,
            "dbms_version": self._check._mongo_version,
            "tags": self._check._get_tags(),
            "cloud_metadata": self._check._config.cloud_metadata,
        }

        collected_collections = 0
        for db_name in self._check.databases_monitored:
            if db_name in MONGODB_SYSTEM_DATABASES:
                self._check.log.debug("Skipping system database %s", db_name)
                continue
            if self._max_collections and collected_collections >= self._max_collections:
                break

            collections = []
            for coll_name in self._check.api_client.list_authorized_collections(
                db_name, limit=self._max_collections_per_database
            ):
                try:
                    collection = self._discover_collection(db_name, coll_name)
                    collections.append(collection)
                    collected_collections += 1
                    if self._max_collections and collected_collections >= self._max_collections:
                        self._check.log.debug("max_collection is configured to %d and reached", self._max_collections)
                        break
                except Exception as e:
                    self._check.log.error("Error collecting schema for %s.%s: %s", db_name, coll_name, e)

            if not collections:
                self._check.log.debug("No collections found for database %s", db_name)
                continue

            # Submit one schema payload per database to avoid hitting the payload size limit
            self._submit_schema_payload(base_payload, db_name, collections)

    def _should_collect_schemas(self) -> bool:
        # Only collect schemas on primary or mongos
        return self._check.deployment_type.is_principal()

    def _discover_collection(self, dbname, collname):
        schema = self._discover_collection_schema(dbname, collname)
        indexes = self._discover_collection_indexes(dbname, collname)
        search_indexes = self._discover_collection_search_indexes(dbname, collname)
        is_sharded = self._check.api_client.is_collection_sharded(dbname, collname)
        return {
            "name": collname,
            "namespace": f"{dbname}.{collname}",
            "sharded": is_sharded,
            "docs": schema,
            "indexes": indexes,
            "search_indexes": search_indexes,
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

        schema_types = defaultdict(set)  # field -> set(types)
        field_prevalence = defaultdict(int)  # (field, type) -> prevalence
        for doc in sampled_docs:
            doc_structure, field_prevalence = self._analyze_doc_structure(
                doc, "", field_prevalence, scale=len(sampled_docs), depth=1
            )
            for key, types in doc_structure.items():
                schema_types[key].update(types)

        schema = []
        for key, types in schema_types.items():
            schema.extend(
                {
                    "name": key,
                    "type": value_type,
                    "prevalence": round(field_prevalence[(key, value_type)], 3),
                }
                for value_type in sorted(types)
            )

        return schema

    def _discover_collection_indexes(self, dbname, collname):
        indexes = self._check.api_client.index_information(dbname, collname)
        return [self._create_index_payload(index_name, index_details) for index_name, index_details in indexes.items()]

    def _create_index_payload(self, index_name, index_details):
        payload = {
            "name": index_name,
            "keys": [
                {
                    "field": field,
                    "type": str(index_type),
                }
                for field, index_type in index_details.get("key", [])
            ],
            "type": self._get_index_type(index_name, index_details),
        }

        # Options represent the index properties, we only include them if they are set
        options = {
            "unique": self._is_index_unique(index_name, index_details),
            "compound": len(index_details.get("key", [])) > 1,
            "hidden": index_details.get("hidden", False),
            "partial": "partialFilterExpression" in index_details,
            "sparse": index_details.get("sparse", False),
            "case_insensitive": self._is_index_case_insensitive(index_details),
            "ttl": index_details.get("expireAfterSeconds"),
        }
        options = {k: v for k, v in options.items() if v}  # Omit falsey values
        payload.update(options)
        return payload

    def _is_index_unique(self, index_name, index_details):
        if index_name == "_id_":
            return True
        return index_details.get("unique", False)

    def _is_index_case_insensitive(self, index_details):
        collation = index_details.get("collation")
        if collation:
            case_level = collation.get("caseLevel")
            if case_level:
                return False
            strength = collation.get("strength")
            return strength == 1 or strength == 2
        return False

    def _get_index_type(self, index_name, index_details):
        if "2dsphereIndexVersion" in index_details:
            return "geospatial"
        if "textIndexVersion" in index_details:
            return "text"
        if index_name == "$**_1":
            return "wildcard"
        for _, value in index_details.get("key", []):
            if value == "hashed":
                return "hashed"
            if value == "2d":
                return "geospatial"
        return "regular"

    def _discover_collection_search_indexes(self, dbname, collname):
        if not self._collect_search_indexes:
            self._check.log.debug("Search indexes collection is disabled")
            return []

        if not self._check.deployment_type.hosting_type == HostingType.ATLAS:
            self._check.log.debug("Search indexes are only supported for Atlas deployments")
            return []

        try:
            search_indexes = self._check.api_client.list_search_indexes(dbname, collname)
            return [self._create_search_index_payload(search_index) for search_index in search_indexes]
        except Exception as e:
            self._check.log.error("Error collecting search indexes for %s.%s: %s", dbname, collname, e)
            return []

    def _create_search_index_payload(self, search_index):
        definition_mappings = search_index.get("latestDefinition", {}).get("mappings", {})
        definition_mappings_fields = definition_mappings.get("fields", {})
        payload = {
            "name": search_index["name"],
            "type": search_index["type"],
            "status": search_index["status"],
            "queryable": search_index["queryable"],
            "version": str(search_index.get("latestDefinitionVersion", {}).get("version", "")),
            "mappings": {
                "dynamic": definition_mappings.get("dynamic"),
                "fields": [
                    {
                        "field": field_name,
                        "type": field_details["type"],
                    }
                    for field_name, field_details in definition_mappings_fields.items()
                ],
            },
        }
        return payload

    def _submit_schema_payload(self, base_payload, dbname, collections):
        payload = {
            **base_payload,
            "timestamp": time.time() * 1000,
            "metadata": [
                {
                    "name": dbname,
                    "collections": collections,
                }
            ],
        }
        json_payload = json_util.dumps(payload)
        self._check.log.debug(
            "Submitting schema payload for %s with size %d", dbname, len(json_payload.encode("utf-8"))
        )
        self._check.database_monitoring_metadata(json_payload)

    def _analyze_doc_structure(self, document, path, field_prevalence, scale, depth=1):
        '''
        Function to analyze the structure of a document and return the field types and counts
        '''
        structure = defaultdict(set)
        for key, value in document.items():
            full_path = f"{path}.{key}" if path else key
            value_type = self._determine_value_type(value)
            structure[full_path].add(value_type)

            if isinstance(value, dict):
                field_prevalence[(full_path, value_type)] += 1 / scale
                if depth < self._max_depth:
                    nested_structure, field_prevalence = self._analyze_doc_structure(
                        value, full_path, field_prevalence, scale=scale, depth=depth + 1
                    )
                    for nested_key, nested_types in nested_structure.items():
                        structure[nested_key].update(nested_types)
            elif isinstance(value, list):
                # Count the array field once per document
                field_prevalence[(full_path, value_type)] += 1 / scale
                for item in value:
                    if isinstance(item, dict) and depth < self._max_depth:
                        nested_structure, field_prevalence = self._analyze_doc_structure(
                            item, full_path, field_prevalence, scale=len(value) * scale, depth=depth + 1
                        )
                        for nested_key, nested_types in nested_structure.items():
                            structure[nested_key].update(nested_types)
            else:
                field_prevalence[(full_path, value_type)] += 1 / scale

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
