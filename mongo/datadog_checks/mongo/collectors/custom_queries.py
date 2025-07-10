# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import datetime
import re
from copy import deepcopy

import dateutil.parser
import pymongo
from dateutil.tz import tzutc

from datadog_checks.mongo.api import CRITICAL_FAILURE
from datadog_checks.mongo.collectors.base import MongoCollector
from datadog_checks.mongo.common import (
    ALLOWED_CUSTOM_METRICS_TYPES,
    ALLOWED_CUSTOM_QUERIES_COMMANDS,
    ReplicaSetDeployment,
)

MONGO_DATE_EXPRESSIONS = {
    r"ISODate\(\s*\'(.*?)\'\s*\)": (lambda m: dateutil.parser.isoparse(m.groups()[0])),
    r"ISODate\(\s*\)|Date\(\s*\)": (lambda m: datetime.datetime.now(tz=tzutc())),
    r"new\s*Date\(ISODate\(\s*\)\.getTime\(\s*\)((\s*[+\-*\/]\s*(\d+))*)\s*\)": (
        lambda m: datetime.datetime.now(tz=tzutc()) + datetime.timedelta(milliseconds=eval(m.groups()[0]))
    ),
}


def replace_value(obj, log):
    if isinstance(obj, str):
        new_v = obj
        for expression, f in MONGO_DATE_EXPRESSIONS.items():
            m = re.match(expression, obj)
            if m:
                log.debug("match: %s", obj)
                log.debug("groups: %s", m.groups())
                new_v = f(m)
                break
        return new_v
    return obj


def replace_datetime(obj, log):
    log.debug("replace_datetime in %s", obj)
    # Recur as necessary into dicts and lists
    if isinstance(obj, dict):
        return {k: replace_datetime(v, log) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [replace_datetime(item, log) for item in obj]
    return replace_value(obj, log)


class CustomQueriesCollector(MongoCollector):
    """A collector dedicated to running custom queries defined in the configuration."""

    def __init__(self, check, db_name, tags, custom_queries):
        super(CustomQueriesCollector, self).__init__(check, tags)
        self.custom_queries = custom_queries
        self.db_name = db_name

    def compatible_with(self, deployment):
        # Can theoretically be run on any node as long as it contains data.
        # i.e Arbiters are ruled out
        if isinstance(deployment, ReplicaSetDeployment) and deployment.is_arbiter:
            self.log.debug("CustomQueriesCollector cannot be run on arbiter nodes.")
            return False
        return True

    @staticmethod
    def _extract_command_from_mongo_query(mongo_query):
        """Extract the command (find, count or aggregate) from the query. Even though mongo and pymongo are supposed
        to work with the query as a single document, pymongo expects the command to be the `first` element of the
        query dict.
        Because python 2 dicts are not ordered, the command is extracted to be later run as the first argument
        of pymongo `runcommand`
        """
        for command in ALLOWED_CUSTOM_QUERIES_COMMANDS:
            if command in mongo_query:
                return command
        raise ValueError("Custom query command must be of type {}".format(ALLOWED_CUSTOM_QUERIES_COMMANDS))

    def _get_submission_method(self, method_name):
        if method_name not in ALLOWED_CUSTOM_METRICS_TYPES:
            raise ValueError('Metric type {} is not one of {}.'.format(method_name, ALLOWED_CUSTOM_METRICS_TYPES))
        return getattr(self.check, method_name)

    def _collect_custom_metrics_for_query(self, api, raw_query):
        """Validates the raw_query object, executes the mongo query then submits the metrics to Datadog"""
        db_name = raw_query.get('database', self.db_name)
        db = api[db_name]
        tags = self.base_tags + ["db:{}".format(db_name)]
        metric_prefix = raw_query.get('metric_prefix')
        if not metric_prefix:  # no cov
            raise ValueError("Custom query field `metric_prefix` is required")
        metric_prefix = metric_prefix.rstrip('.')

        mongo_query = deepcopy(raw_query.get('query'))
        if not mongo_query:  # no cov
            raise ValueError("Custom query field `query` is required")
        # The mongo command to run (find, aggregate, count...)
        mongo_command = self._extract_command_from_mongo_query(mongo_query)
        # The value of the command, it is usually the collection name on which to run the query.
        mongo_command_value = mongo_query[mongo_command]
        del mongo_query[mongo_command]
        if mongo_command not in ALLOWED_CUSTOM_QUERIES_COMMANDS:
            raise ValueError("Custom query command must be of type {}".format(ALLOWED_CUSTOM_QUERIES_COMMANDS))

        submit_method = self.gauge
        fields = []

        if mongo_command == 'count':
            count_type = raw_query.get('count_type')
            if not count_type:  # no cov
                raise ValueError('Custom query field `count_type` is required with a `count` query')
            submit_method = self._get_submission_method(count_type)
        else:
            fields = raw_query.get('fields')
            if not fields:  # no cov
                raise ValueError('Custom query field `fields` is required')

        for field in fields:
            field_name = field.get('field_name')
            if not field_name:  # no cov
                raise ValueError('Field `field_name` is required for metric_prefix `{}`'.format(metric_prefix))

            name = field.get('name')
            if not name:  # no cov
                raise ValueError('Field `name` is required for metric_prefix `{}`'.format(metric_prefix))

            field_type = field.get('type')
            if not field_type:  # no cov
                raise ValueError('Field `type` is required for metric_prefix `{}`'.format(metric_prefix))
            if field_type not in ALLOWED_CUSTOM_METRICS_TYPES + ['tag']:
                raise ValueError('Field `type` must be one of {}'.format(ALLOWED_CUSTOM_METRICS_TYPES + ['tag']))

        try:
            # This is where it is necessary to extract the command and its argument from the query to pass it as the
            # first two params.
            self.log.debug("mongo_command: %s", mongo_command)
            self.log.debug("mongo_command_value: %s", mongo_command_value)
            mongo_query = replace_datetime(mongo_query, self.log)
            self.log.debug("mongo_query: %s", mongo_query)
            result = db.command(mongo_command, mongo_command_value, **mongo_query)
            if result['ok'] == 0:
                raise pymongo.errors.PyMongoError(result['errmsg'])
        except pymongo.errors.PyMongoError:
            self.log.error("Failed to run custom query for metric %s", metric_prefix)
            raise

        # `1` is Mongo default value for commands that are collection agnostics.
        if str(mongo_command_value) == '1':
            # https://github.com/mongodb/mongo-python-driver/blob/01e34cebdb9aac96c72ddb649e9b0040a0dfd3a0/pymongo/aggregation.py#L208
            collection_name = '{}.{}'.format(db_name, mongo_command)
        else:
            collection_name = mongo_command_value

        tags.append('collection:{}'.format(collection_name))
        tags.extend(raw_query.get('tags', []))

        if mongo_command == 'count':
            # A count query simply returns a number, no need to iterate through it.
            submit_method(metric_prefix, result['n'], tags)
            return

        cursor = pymongo.command_cursor.CommandCursor(
            pymongo.collection.Collection(db, collection_name), result['cursor'], None
        )
        empty_result_set = True

        for row in cursor:
            self.log.debug("row: %s", row)
            empty_result_set = False
            metric_info = []
            query_tags = list(tags)

            for field in fields:
                field_name = field['field_name']
                if field_name not in row:
                    # Each row can have different fields, do not fail here.
                    continue

                field_type = field['type']
                if field_type == 'tag':
                    tag_name = field['name']
                    query_tags.append('{}:{}'.format(tag_name, row[field_name]))
                else:
                    metric_suffix = field['name']
                    submit_method = self._get_submission_method(field_type)
                    metric_name = '{}.{}'.format(metric_prefix, metric_suffix)
                    try:
                        metric_info.append((metric_name, float(row[field_name]), submit_method))
                    except (TypeError, ValueError):
                        continue

            for metric_name, metric_value, submit_method in metric_info:
                submit_method(metric_name, metric_value, tags=query_tags)

        if empty_result_set:
            raise Exception('Custom query returned an empty result set.')

    def collect(self, api):
        for raw_query in self.custom_queries:
            try:
                self._collect_custom_metrics_for_query(api, raw_query)
            except CRITICAL_FAILURE as e:
                raise e  # Critical failures must bubble up to trigger a CRITICAL service check.
            except Exception as e:
                metric_prefix = raw_query.get('metric_prefix')
                self.log.warning("Errors while collecting custom metrics with prefix %s", metric_prefix, exc_info=e)
