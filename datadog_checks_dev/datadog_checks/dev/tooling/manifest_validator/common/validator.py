# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import abc
import json
import os
from typing import Dict

import six

from datadog_checks.dev.tooling.datastructures import JSONDict
from datadog_checks.dev.tooling.git import git_show_file
from datadog_checks.dev.tooling.utils import get_metadata_file, has_logs, is_metric_in_metadata_file, read_metadata_rows

from ..constants import V1, V2


class ValidationResult(object):
    def __init__(self):
        self.failed = False
        self.fixed = False
        self.messages = {'success': [], 'warning': [], 'failure': [], 'info': []}

    def __str__(self):
        return '\n'.join(['\n'.join(messages) for messages in self.messages.values()])

    def __repr__(self):
        return str(self)


@six.add_metaclass(abc.ABCMeta)
class BaseManifestValidator(object):
    def __init__(
        self,
        is_extras=False,
        is_marketplace=False,
        check_in_extras=True,
        check_in_marketplace=True,
        ctx=None,
        version=V1,
        skip_if_errors=False,
    ):
        self.result = ValidationResult()
        self.is_extras = is_extras
        self.is_marketplace = is_marketplace
        self.check_in_extras = check_in_extras
        self.check_in_markeplace = check_in_marketplace
        self.ctx = ctx
        self.version = version
        self.skip_if_errors = skip_if_errors

    def should_validate(self):
        """Determine if validator applicable given the current repo.

        Logic will always validate integrations-core, but flags exist to
        selectively include extras and marketplace
        """
        if not self.is_extras and not self.is_marketplace:
            return True
        if self.is_extras and self.check_in_extras:
            return True
        if self.is_marketplace and self.check_in_markeplace:
            return True
        return False

    def validate(self, check_name, manifest, should_fix):
        # type: (str, Dict, bool) -> None
        """Validates the decoded manifest. Will perform inline changes if fix is true"""
        raise NotImplementedError

    def fail(self, error_message):
        self.result.failed = True
        self.result.messages['failure'].append(error_message)

    def fix(self, problem, solution):
        self.result.warning_msg = problem
        self.result.success_msg = solution
        self.result.fixed = True
        self.result.failed = False

    def __repr__(self):
        return str(self.result)


class MaintainerValidator(BaseManifestValidator):

    MAINTAINER_PATH = {V1: '/maintainer', V2: '/author/support_email'}

    def validate(self, check_name, decoded, fix):
        if not self.should_validate():
            return
        correct_maintainer = 'help@datadoghq.com'

        path = self.MAINTAINER_PATH[self.version]
        maintainer = decoded.get_path(path)

        if not maintainer.isascii():
            self.fail(f'  `maintainer` contains non-ascii character: {maintainer}')
            return
        if maintainer != correct_maintainer:
            output = f'  incorrect `maintainer`: {maintainer}'
            if fix:
                decoded.set_path(path, correct_maintainer)
                self.fix(output, f'  new `maintainer`: {correct_maintainer}')
            else:
                self.fail(output)


class MetricsMetadataValidator(BaseManifestValidator):

    METADATA_PATH = {V1: "/assets/metrics_metadata", V2: "/assets/integration/metrics/metadata_path"}

    def validate(self, check_name, decoded, fix):
        # metrics_metadata
        path = self.METADATA_PATH[self.version]
        metadata_in_manifest = decoded.get_path(path)

        metadata_file = get_metadata_file(check_name)
        metadata_file_exists = os.path.isfile(metadata_file)

        if not metadata_in_manifest and metadata_file_exists:
            # There is a metadata.csv file but no entry in the manifest.json
            self.fail('  metadata.csv exists but not defined in the manifest.json of {}'.format(check_name))
        elif metadata_in_manifest and not metadata_file_exists:
            # There is an entry in the manifest.json file but the referenced csv file does not exist.
            self.fail('  metrics_metadata in manifest.json references a non-existing file: {}.'.format(metadata_file))


class MetricToCheckValidator(BaseManifestValidator):
    METRIC_TO_CHECK_EXCLUDE_LIST = {
        'openstack.controller',  # "Artificial" metric, shouldn't be listed in metadata file.
        'riakcs.bucket_list_pool.workers',  # RiakCS 2.1 metric, but metadata.csv lists RiakCS 2.0 metrics only.
    }
    METADATA_PATH = {V1: "/assets/metrics_metadata", V2: "/assets/integration/metrics/metadata_path"}
    METRIC_PATH = {V1: "/metric_to_check", V2: "/assets/integration/metrics/check"}
    PRICING_PATH = {V1: "/pricing", V2: "/pricing"}

    def validate(self, check_name, decoded, _):
        if not self.should_validate() or check_name == 'snmp' or check_name == 'moogsoft':
            return

        metadata_path = self.METADATA_PATH[self.version]
        metadata_in_manifest = decoded.get_path(metadata_path)

        # metric_to_check
        metric_path = self.METRIC_PATH[self.version]
        metric_to_check = decoded.get_path(metric_path)

        pricing_path = self.PRICING_PATH[self.version]
        pricing = decoded.get_path(pricing_path) or []

        if metric_to_check:
            metrics_to_check = metric_to_check if isinstance(metric_to_check, list) else [metric_to_check]
            for metric in metrics_to_check:
                # if metric found in pricing, skip and continue evaluating other metrics_to_check
                if any(p.get('metric') == metric for p in pricing):
                    continue
                metric_integration_check_name = check_name
                # snmp vendor specific integrations define metric_to_check
                # with metrics from `snmp` integration
                if check_name.startswith('snmp_') and not metadata_in_manifest:
                    metric_integration_check_name = 'snmp'
                if (
                    not is_metric_in_metadata_file(metric, metric_integration_check_name)
                    and metric not in self.METRIC_TO_CHECK_EXCLUDE_LIST
                ):
                    self.fail(f'  metric_to_check not in metadata.csv: {metric!r}')

        elif metadata_in_manifest:
            # if we have a metadata.csv file but no `metric_to_check` raise an error
            metadata_file = get_metadata_file(check_name)
            if os.path.isfile(metadata_file):
                for _, row in read_metadata_rows(metadata_file):
                    # there are cases of metadata.csv files with just a header but no metrics
                    if row:
                        self.fail('  metric_to_check not included in manifest.json')


class ImmutableAttributesValidator(BaseManifestValidator):
    """
    Ensure that immutable attributes haven't changed
    Skip if the manifest is a new file (i.e. new integration) or if the manifest is being upgraded to V2
    """

    MANIFEST_VERSION_PATH = "manifest_version"

    IMMUTABLE_FIELD_PATHS = {
        V1: ("integration_id", "display_name", "guid"),
        V2: (
            "app_id",
            "app_uuid",
            "assets/integration/id",
            "assets/integration/source_type_name",
        ),
    }

    SHORT_NAME_PATHS = {
        V1: (
            "assets/dashboards",
            "assets/monitors",
            "assets/saved_views",
        ),
        V2: (
            "assets/dashboards",
            "assets/monitors",
            "assets/saved_views",
        ),
    }

    def validate(self, check_name, decoded, fix):
        # Check if previous version of manifest exists
        # If not, this is a new file so this validation is skipped
        try:
            previous = git_show_file(path=f"{check_name}/manifest.json", ref="origin/master")
            previous_manifest = JSONDict(json.loads(previous))
        except Exception:
            self.result.messages['info'].append(
                "  skipping check for changed fields: integration not on default branch"
            )
            return

        # Skip this validation if the manifest is being updated from 1.0.0 -> 2.0.0
        current_manifest = decoded
        if (
            previous_manifest[self.MANIFEST_VERSION_PATH] == "1.0.0"
            and current_manifest[self.MANIFEST_VERSION_PATH] == "2.0.0"
        ):
            self.result.messages['info'].append("  skipping check for changed fields: manifest version was upgraded")
            return

        # Check for differences in immutable attributes
        for key_path in self.IMMUTABLE_FIELD_PATHS[self.version]:
            previous_value = previous_manifest.get_path(key_path)
            current_value = current_manifest.get_path(key_path)

            if previous_value != current_value:
                output = f'Attribute `{current_value}` at `{key_path}` is not allowed to be modified. Please revert it \
to the original value `{previous_value}`.'
                self.fail(output)

        # Check for differences in `short_name` keys
        for key_path in self.SHORT_NAME_PATHS[self.version]:
            previous_short_name_dict = previous_manifest.get_path(key_path) or {}
            current_short_name_dict = current_manifest.get_path(key_path) or {}

            # Every `short_name` in the prior manifest must be in the current manifest
            # The key cannot change and it cannot be removed
            previous_short_names = previous_short_name_dict.keys()
            current_short_names = set(current_short_name_dict.keys())
            for short_name in previous_short_names:
                if short_name not in current_short_names:
                    output = f'Short name `{short_name}` at `{key_path}` is not allowed to be modified. \
Please revert to original value.'
                    self.fail(output)


class LogsCategoryValidator(BaseManifestValidator):
    """If an integration defines logs it should have the log collection category"""

    LOG_COLLECTION_CATEGORY = {V1: "log collection", V2: "Category::Log Collection"}

    CATEGORY_PATH = {V1: "/categories", V2: "/classifier_tags"}

    IGNORE_LIST = {
        'databricks',  # Logs are provided by Spark
        'docker_daemon',
        'ecs_fargate',  # Logs are provided by FireLens or awslogs
        'cassandra_nodetool',  # Logs are provided by cassandra
        'jmeter',
        'kafka_consumer',  # Logs are provided by kafka
        'kubernetes',
        'pan_firewall',
        'altostra',
        'hasura_cloud',
        'sqreen',
    }

    def validate(self, check_name, decoded, fix):
        path = self.CATEGORY_PATH[self.version]
        categories = decoded.get_path(path) or []

        check_has_logs = has_logs(check_name)
        log_collection_category = self.LOG_COLLECTION_CATEGORY[self.version]
        check_has_logs_category = log_collection_category in categories

        if check_has_logs == check_has_logs_category or check_name in self.IGNORE_LIST:
            return

        if check_has_logs:
            output = '  required category: ' + log_collection_category
            if fix:
                correct_categories = sorted(categories + [self.LOG_COLLECTION_CATEGORY])
                decoded.set_path(path, correct_categories)
                self.fix(output, f'  new `categories`: {correct_categories}')
            else:
                self.fail(output)
        else:
            output = (
                '  This integration does not have logs, please remove the category: '
                + log_collection_category
                + ' or define the logs properly'
            )
            self.fail(output)
