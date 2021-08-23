#  (C) Datadog, Inc. 2020-present
#  All rights reserved
#  Licensed under a 3-clause BSD style license (see LICENSE)
import abc
import json
import os
from typing import Dict

import requests
import six

from datadog_checks.dev.tooling.commands.console import abort
from datadog_checks.dev.tooling.git import content_changed
from datadog_checks.dev.tooling.utils import get_metadata_file, has_logs, is_metric_in_metadata_file, read_metadata_rows

FIELDS_NOT_ALLOWED_TO_CHANGE = ["id", "source_type_name", "app_id"]

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
    def __init__(
        self, is_extras=False, is_marketplace=False, check_in_extras=True, check_in_marketplace=True, ctx=None
    ):
        self.result = ValidationResult()
        self.is_extras = is_extras
        self.is_marketplace = is_marketplace
        self.check_in_extras = check_in_extras
        self.check_in_markeplace = check_in_marketplace
        self.ctx = ctx

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


class SchemaValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        if not self.should_validate():
            return

        # Get API and APP keys which are needed to call Datadog API
        org_name = self.ctx.obj['org']
        if not org_name:
            abort('No `org` has been set')

        if org_name not in self.ctx.obj['orgs']:
            abort(f'Selected org {org_name} is not in `orgs`')

        org = self.ctx.obj['orgs'][org_name]

        api_key = org.get('api_key')
        if not api_key:
            abort(f'No `api_key` has been set for org `{org_name}`')

        app_key = org.get('app_key')
        if not app_key:
            abort(f'No `app_key` has been set for org `{org_name}`')

        dd_url = org.get('dd_url')
        if not dd_url:
            abort(f'No `dd_url` has been set for org `{org_name}`')

        # TODO FIX URL
        url = f"{dd_url}/api/beta/apps/manifest/validate"

        # prep for upload
        payload = {"data": {"type": "app_manifest", "attributes": decoded}}

        try:
            payload_json = json.dumps(payload)
            r = requests.post(url, data=payload_json, headers={'DD-API-KEY': api_key, 'DD-APPLICATION-KEY': app_key})

            if r.status_code == 400:
                # parse the errors
                errors = "\n".join(r.json()["errors"])
                message = f"Error validating manifest schema:\n{errors}"
                self.fail(message)
            else:
                r.raise_for_status()
        except Exception as e:
            abort(str(e).replace(api_key, '*' * len(api_key)).replace(app_key, '*' * len(app_key)))


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


class MetricsMetadataValidator(ManifestValidator):
    def validate(self, check_name, decoded, fix):
        # metrics_metadata
        metadata_in_manifest = decoded.get('assets', {}).get('integration', {}).get('metrics', {}).get('metadata_path')
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


def get_v2_validators(ctx, is_extras, is_marketplace):
    return [
        SchemaValidator(ctx=ctx),
        # MaintainerValidator(is_extras, is_marketplace, check_in_extras=False, check_in_marketplace=False),
        # MetricsMetadataValidator(),
        # MetricToCheckValidator(),
        # SupportValidator(is_extras, is_marketplace),
        # ImmutableAttributesValidator(),
        # LogsCategoryValidator(),
    ]
