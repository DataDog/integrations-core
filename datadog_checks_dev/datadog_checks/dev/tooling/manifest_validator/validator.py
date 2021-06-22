# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import abc
import os
import uuid
from typing import Dict

import six

from datadog_checks.dev.tooling.constants import get_root
from datadog_checks.dev.tooling.git import content_changed
from datadog_checks.dev.tooling.manifest_validator.schema import get_manifest_schema
from datadog_checks.dev.tooling.utils import (
    get_metadata_file,
    has_logs,
    is_metric_in_metadata_file,
    parse_version_parts,
    read_metadata_rows,
)

FIELDS_NOT_ALLOWED_TO_CHANGE = ["integration_id", "display_name", "guid"]

METRIC_TO_CHECK_EXCLUDE_LIST = {
    'openstack.controller',  # "Artificial" metric, shouldn't be listed in metadata file.
    'riakcs.bucket_list_pool.workers',  # RiakCS 2.1 metric, but metadata.csv lists RiakCS 2.0 metrics only.
}


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
class ManifestValidator(object):
    def __init__(self, is_extras=False, is_marketplace=False, check_in_extras=True, check_in_marketplace=True):
        self.result = ValidationResult()
        self.is_extras = is_extras
        self.is_marketplace = is_marketplace
        self.check_in_extras = check_in_extras
        self.check_in_markeplace = check_in_marketplace

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


class AttributesValidator(ManifestValidator):
    """ attributes are valid"""

    def validate(self, check_name, decoded, fix):
        errors = sorted(get_manifest_schema().iter_errors(decoded), key=lambda e: e.path)
        if errors:
            for error in errors:
                self.fail(f'  {"->".join(map(str, error.absolute_path))} Error: {error.message}')


class GUIDValidator(ManifestValidator):
    all_guids = {}

    def validate(self, check_name, decoded, fix):
        guid = decoded.get('guid')
        if guid in self.all_guids:
            output = f'  duplicate `guid`: `{guid}` from `{self.all_guids[guid]}`'
            if fix:
                new_guid = uuid.uuid4()
                self.all_guids[new_guid] = check_name
                decoded['guid'] = new_guid
                self.fix(output, f'  new `guid`: {new_guid}')
            else:
                self.fail(output)
        elif not guid or not isinstance(guid, str):
            output = '  required non-null string: guid'
            if fix:
                new_guid = uuid.uuid4()
                self.all_guids[new_guid] = check_name
                decoded['guid'] = new_guid
                self.fix(output, f'  new `guid`: {new_guid}')
            else:
                self.fail(output)
        else:
            self.all_guids[guid] = check_name
        return self.result


class ManifestVersionValidator(ManifestValidator):
    def __init__(self, *args, **kwargs):
        super(ManifestVersionValidator, self).__init__(*args, **kwargs)
        self.root = get_root()

    def validate(self, check_name, decoded, fix):
        # manifest_version
        correct_manifest_version = '1.0.0'
        manifest_version = decoded.get('manifest_version')
        version_parts = parse_version_parts(manifest_version)
        if len(version_parts) != 3:
            if not manifest_version:
                output = '  required non-null string: manifest_version'
            else:
                output = f'  invalid `manifest_version`: {manifest_version}'

            if fix:
                version_parts = parse_version_parts(correct_manifest_version)
                decoded['manifest_version'] = correct_manifest_version
                self.fix(output, f'  new `manifest_version`: {correct_manifest_version}')
            else:
                self.fail(output)

        if len(version_parts) == 3:
            about_exists = os.path.isfile(
                os.path.join(self.root, check_name, 'datadog_checks', check_name, '__about__.py')
            )
            if version_parts >= [1, 0, 0]:
                if 'version' in decoded and about_exists:
                    output = '  outdated field: version'

                    if fix:
                        del decoded['version']
                        self.fix(output, '  removed field: version')
                    else:
                        self.fail(output)
            elif about_exists:
                output = f'  outdated `manifest_version`: {manifest_version}'

                if fix:
                    decoded['manifest_version'] = correct_manifest_version
                    self.fix(output, f'  new `manifest_version`: {correct_manifest_version}')
                    if 'version' in decoded:
                        del decoded['version']
                        self.result.messages['success'].append('  removed field: version')
                else:
                    self.fail(output)
            else:
                version = decoded.get('version')
                version_parts = parse_version_parts(version)
                if len(version_parts) != 3:
                    if not version:
                        output = '  required non-null string: version'
                    else:
                        output = f'  invalid `version`: {version}'
                    self.fail(output)


class MaintainerValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        if not self.should_validate():
            return
        correct_maintainer = 'help@datadoghq.com'
        maintainer = decoded.get('maintainer')
        if not maintainer.isascii():
            self.fail(f'  `maintainer` contains non-ascii character: {maintainer}')
            return
        if maintainer != correct_maintainer:
            output = f'  incorrect `maintainer`: {maintainer}'
            if fix:
                decoded['maintainer'] = correct_maintainer

                self.fix(output, f'  new `maintainer`: {correct_maintainer}')
            else:
                self.fail(output)


class NameValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        correct_name = check_name
        name = decoded.get('name')
        if not isinstance(name, str) or name.lower() != correct_name.lower():
            output = f'  incorrect `name`: {name}'
            if fix:
                decoded['name'] = correct_name
                self.fix(output, f'  new `name`: {correct_name}')
            else:
                self.fail(output)


class MetricsMetadataValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        # metrics_metadata
        metadata_in_manifest = decoded.get('assets', {}).get('metrics_metadata')
        metadata_file = get_metadata_file(check_name)
        metadata_file_exists = os.path.isfile(metadata_file)
        if not metadata_in_manifest and metadata_file_exists:
            # There is a metadata.csv file but no entry in the manifest.json
            self.fail('  metadata.csv exists but not defined in the manifest.json of {}'.format(check_name))
        elif metadata_in_manifest and not metadata_file_exists:
            # There is an entry in the manifest.json file but the referenced csv file does not exist.
            self.fail('  metrics_metadata in manifest.json references a non-existing file: {}.'.format(metadata_file))


class MetricToCheckValidator(ManifestValidator):
    def validate(self, check_name, decoded, _):
        if not self.should_validate() or check_name == 'snmp' or check_name == 'moogsoft':
            return
        metadata_in_manifest = decoded.get('assets', {}).get('metrics_metadata')
        # metric_to_check
        metric_to_check = decoded.get('metric_to_check')
        pricing = decoded.get('pricing', [])
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
                    and metric not in METRIC_TO_CHECK_EXCLUDE_LIST
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


class SupportValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        if self.is_extras:
            correct_support = 'contrib'
        elif self.is_marketplace:
            correct_support = 'partner'
        else:
            correct_support = 'core'

        support = decoded.get('support')
        if support != correct_support:
            output = f'  incorrect `support`: {support}'
            if fix:
                decoded['support'] = correct_support
                self.fix(output, f'  new `support`: {correct_support}')
            else:
                self.fail(output)


class IsPublicValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        correct_is_public = True
        is_public = decoded.get('is_public')
        if not isinstance(is_public, bool):
            output = '  required boolean: is_public'

            if fix:
                decoded['is_public'] = correct_is_public
                self.fix(output, f'  new `is_public`: {correct_is_public}')
            else:
                self.fail(output)


class ImmutableAttributesValidator(ManifestValidator):
    """Ensure attributes haven't changed
    Skip if the manifest is a new file (i.e. new integration)
    """

    def validate(self, check_name, decoded, fix):
        manifest_fields_changed = content_changed(file_glob=f"{check_name}/manifest.json")
        if 'new file' not in manifest_fields_changed:
            for field in FIELDS_NOT_ALLOWED_TO_CHANGE:
                if field in manifest_fields_changed:
                    output = f'Attribute `{field}` is not allowed to be modified. Please revert to original value'
                    self.fail(output)
        else:
            self.result.messages['info'].append(
                "  skipping check for changed fields: integration not on default branch"
            )


class LogsCategoryValidator(ManifestValidator):
    """If an integration defines logs it should have the log collection category"""

    LOG_COLLECTION_CATEGORY = "log collection"
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
        categories = decoded.get('categories')
        check_has_logs = has_logs(check_name)
        check_has_logs_category = self.LOG_COLLECTION_CATEGORY in categories

        if check_has_logs == check_has_logs_category or check_name in self.IGNORE_LIST:
            return

        if check_has_logs:
            output = '  required category: ' + self.LOG_COLLECTION_CATEGORY
            if fix:
                correct_categories = categories + [self.LOG_COLLECTION_CATEGORY]
                decoded['categories'] = correct_categories
                self.fix(output, f'  new `categories`: {correct_categories}')
            else:
                self.fail(output)
        else:
            output = (
                '  This integration does not have logs, please remove the category: '
                + self.LOG_COLLECTION_CATEGORY
                + ' or define the logs properly'
            )
            self.fail(output)


def get_all_validators(is_extras, is_marketplace):
    return [
        AttributesValidator(),
        GUIDValidator(),
        ManifestVersionValidator(),
        MaintainerValidator(is_extras, is_marketplace, check_in_extras=False, check_in_marketplace=False),
        NameValidator(),
        MetricsMetadataValidator(),
        MetricToCheckValidator(),
        SupportValidator(is_extras, is_marketplace),
        IsPublicValidator(),
        ImmutableAttributesValidator(),
        LogsCategoryValidator(),
    ]
