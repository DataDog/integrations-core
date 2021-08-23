# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
import uuid

from datadog_checks.dev.tooling.constants import get_root
from datadog_checks.dev.tooling.manifest_validator.common.validator import (
    ImmutableAttributesValidator,
    IsPublicValidator,
    LogsCategoryValidator,
    MaintainerValidator,
    ManifestValidator,
    MetricsMetadataValidator,
    MetricToCheckValidator,
    NameValidator,
)
from datadog_checks.dev.tooling.manifest_validator.v1.schema import get_manifest_schema
from datadog_checks.dev.tooling.utils import has_logs, is_package, parse_version_parts


class AttributesValidator(ManifestValidator):
    """Check that attributes are valid"""

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


class SupportedOSValidator(ManifestValidator):
    """If an integration contains python or logs configuration, the supported_os field should not be empty."""

    def validate(self, check_name, decoded, _):
        supported_os = decoded.get('supported_os')
        check_has_logs = has_logs(check_name)
        check_has_python = is_package(check_name)

        if not supported_os and (check_has_logs or check_has_python):
            output = f'Attribute `supported_os` in {check_name}/manifest.json should not be empty.'
            self.fail(output)


def get_v1_validators(is_extras, is_marketplace):
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
        SupportedOSValidator(),
    ]
