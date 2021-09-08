#  (C) Datadog, Inc. 2020-present
#  All rights reserved
#  Licensed under a 3-clause BSD style license (see LICENSE)
import json

import requests

import datadog_checks.dev.tooling.manifest_validator.common.validator as common
from datadog_checks.dev.tooling.manifest_validator.common.validator import BaseManifestValidator

from ..constants import V2

METRIC_TO_CHECK_EXCLUDE_LIST = {
    'openstack.controller',  # "Artificial" metric, shouldn't be listed in metadata file.
    'riakcs.bucket_list_pool.workers',  # RiakCS 2.1 metric, but metadata.csv lists RiakCS 2.0 metrics only.
}


class DisplayOnPublicValidator(BaseManifestValidator):
    def validate(self, check_name, decoded, fix):
        correct_is_public = True
        path = '/display_on_public_website'
        is_public = decoded.get_path(path)
        if not isinstance(is_public, bool):
            output = '  required boolean: display_on_public_website'

            if fix:
                decoded.set_path(path, correct_is_public)
                self.fix(output, f'  new `display_on_public_website`: {correct_is_public}')
            else:
                self.fail(output)


class SchemaValidator(BaseManifestValidator):
    def validate(self, check_name, decoded, fix):
        if not self.should_validate():
            return

        # Get API and APP keys which are needed to call Datadog API
        org_name = self.ctx.obj['org']
        if not org_name:
            self.fail('No `org` has been set')

        if org_name not in self.ctx.obj['orgs']:
            self.fail(f'Selected org {org_name} is not in `orgs`')

        org = self.ctx.obj['orgs'][org_name]

        api_key = org.get('api_key')
        if not api_key:
            self.fail(f'No `api_key` has been set for org `{org_name}`')

        app_key = org.get('app_key')
        if not app_key:
            self.fail(f'No `app_key` has been set for org `{org_name}`')

        dd_url = org.get('dd_url')
        if not dd_url:
            self.fail(f'No `dd_url` has been set for org `{org_name}`')

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
            self.fail(str(e).replace(api_key, '*' * len(api_key)).replace(app_key, '*' * len(app_key)))


def get_v2_validators(ctx, is_extras, is_marketplace):
    return [
        common.MaintainerValidator(
            is_extras, is_marketplace, check_in_extras=False, check_in_marketplace=False, version=V2
        ),
        common.MetricsMetadataValidator(version=V2),
        common.MetricToCheckValidator(version=V2),
        common.ImmutableAttributesValidator(version=V2),
        common.LogsCategoryValidator(version=V2),
        DisplayOnPublicValidator(version=V2),
        # keep SchemaValidator last, and avoid running this validation if errors already found
        SchemaValidator(ctx=ctx, version=V2, skip_if_errors=True),
    ]
