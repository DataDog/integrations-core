# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import abc
import os
from typing import Dict

import six

from datadog_checks.dev.tooling.git import content_changed
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


class NameValidator(BaseManifestValidator):

    NAME_PATH = {V1: '/name', V2: '/assets/integration/id'}

    def validate(self, check_name, decoded, fix):
        correct_name = check_name

        path = self.NAME_PATH[self.version]
        name = decoded.get_path(path)

        if check_name.startswith('datadog') and check_name != 'datadog_cluster_agent':
            self.fail(f'  An integration check folder cannot start with `datadog`: {check_name}')
        if not isinstance(name, str) or name.lower() != correct_name.lower():
            output = f'  incorrect `name`: {name}'
            if fix:
                decoded.set_path(path, correct_name)
                self.fix(output, f'  new `name`: {correct_name}')
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

        pricing = decoded.get_path("/pricing") or []

        if metric_to_check:
            metrics_to_check = metric_to_check if isinstance(metric_to_check, list) else [metric_to_check]
            if any(p.get('metric') in metrics_to_check for p in pricing):
                return
            for metric in metrics_to_check:
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


class IsPublicValidator(BaseManifestValidator):
    PUBLIC_PATH = {V1: "/is_public", V2: "/display_on_public_website"}

    def validate(self, check_name, decoded, fix):
        correct_is_public = True
        path = self.PUBLIC_PATH[self.version]
        is_public = decoded.get_path(path)
        if not isinstance(is_public, bool):
            output = '  required boolean: is_public'

            if fix:
                decoded.set_path(path, correct_is_public)
                self.fix(output, f'  new `is_public`: {correct_is_public}')
            else:
                self.fail(output)


class ImmutableAttributesValidator(BaseManifestValidator):
    """Ensure attributes haven't changed
    Skip if the manifest is a new file (i.e. new integration)
    """

    FIELDS_NOT_ALLOWED_TO_CHANGE = {
        V1: ("integration_id", "display_name", "guid"),
        V2: ("id", "source_type_name", "app_id"),
    }

    def validate(self, check_name, decoded, fix):
        manifest_fields_changed = content_changed(file_glob=f"{check_name}/manifest.json")
        if 'new file' not in manifest_fields_changed:
            for field in self.FIELDS_NOT_ALLOWED_TO_CHANGE[self.version]:
                if field in manifest_fields_changed:
                    output = f'Attribute `{field}` is not allowed to be modified. Please revert to original value'
                    self.fail(output)
        else:
            self.result.messages['info'].append(
                "  skipping check for changed fields: integration not on default branch"
            )


class LogsCategoryValidator(BaseManifestValidator):
    """If an integration defines logs it should have the log collection category"""

    LOG_COLLECTION_CATEGORY = {V1: "log collection", V2: "Category::Log Collection"}

    CATEGORY_PATH = {V1: "/categories", V2: "/tile/classifier_tags"}

    IGNORE_LIST = {
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
