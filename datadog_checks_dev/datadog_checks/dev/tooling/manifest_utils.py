# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os

from ..fs import file_exists
from .commands.console import abort
from .constants import get_root
from .datastructures import JSONDict
from .manifest_validator.constants import V1, V2
from .utils import load_manifest

NON_INTEGRATION_PATHS = [
    "datadog_checks_base",
    "datadog_checks_dependency_provider",
    "datadog_checks_dev",
    "datadog_checks_downloader",
]


class Manifest:
    """
    Class to retrieve a manifest class based on the check/manifest_version
    This also supports the case of querying file information about the Agent
    """

    # add version constants to avoid extra imports
    V1 = V1
    V2 = V2

    @staticmethod
    def load_manifest(check):
        """
        Return an accessor class based on the check or manifest_version provided
        Return None for known non-valid checks and
        abort for any non-known invalid manifests
        """
        if check in NON_INTEGRATION_PATHS:
            return None

        raw_manifest_json = load_manifest(check)
        manifest_version = raw_manifest_json.get("manifest_version")

        if check == 'agent':
            return Agent(check, {})
        if manifest_version == "1.0.0":
            return ManifestV1(check, raw_manifest_json)
        elif manifest_version == "2.0.0":
            return ManifestV2(check, raw_manifest_json)
        else:
            abort(f"Unsupported check: {check} or manifest_version: {manifest_version}")


class Agent:
    def __init__(self, check_name, manifest_json):
        self._check_name = check_name
        self._manifest_json = manifest_json
        self.version = None

    def get_config_spec(self):
        return os.path.join(get_root(), 'pkg', 'config', 'conf_spec.yaml')


class ManifestV1:
    """
    Getters for the V1 Manifest
    These should match whats found in the ManifestV2 class
    """

    def __init__(self, check_name, manifest_json):
        self._check_name = check_name
        self._manifest_json = JSONDict(manifest_json)
        self.version = V1

    def get_path(self, path):
        return self._manifest_json.get(path)

    def get_display_name(self):
        return self._manifest_json['display_name']

    def get_app_id(self):
        return None

    def get_app_uuid(self):
        return None

    def get_metric_prefix(self):
        return self._manifest_json['metric_prefix']

    def get_eula_from_manifest(self):
        path = self._manifest_json['terms']['eula']
        path = os.path.join(get_root(), self._check_name, *path.split('/'))
        return path, file_exists(path)

    def get_metadata_path(self):
        return self._manifest_json.get_path("/assets/metrics_metadata")

    def get_service_checks_path(self):
        return self._manifest_json["assets"]["service_checks"]

    def get_config_spec(self):
        path = self._manifest_json.get('assets', {}).get('configuration', {}).get('spec', '')
        return os.path.join(get_root(), self._check_name, *path.split('/'))

    def has_integration(self):
        # we assume all V1 manifests have an integration, this should avoid breaking any existing validations
        return True


class ManifestV2:
    """
    Getters for the V2 Manifest
    These should match whats found in the ManifestV1 class
    """

    def __init__(self, check_name, manifest_json):
        self._check_name = check_name
        self._manifest_json = JSONDict(manifest_json)
        self.version = V2

    def get_path(self, path):
        return self._manifest_json.get(path)

    def get_display_name(self):
        return self._manifest_json.get_path("/assets/integration/source_type_name")

    def get_app_id(self):
        return self._manifest_json['app_id']

    def get_app_uuid(self):
        return self._manifest_json['app_uuid']

    def get_metric_prefix(self):
        return self._manifest_json.get_path("/assets/integration/metrics/prefix") or ''

    def get_eula_from_manifest(self):
        path = self._manifest_json['legal_terms']['eula']
        path = os.path.join(get_root(), self._check_name, *path.split('/'))
        return path, file_exists(path)

    def get_metadata_path(self):
        return self._manifest_json.get_path("/assets/integration/metrics/metadata_path")

    def get_service_checks_path(self):
        return self._manifest_json.get_path("/assets/integration/service_checks/metadata_path")

    def get_config_spec(self):
        path = self._manifest_json.get_path('/assets/integration/configuration/spec') or ''
        return os.path.join(get_root(), self._check_name, *path.split('/'))

    def has_integration(self):
        return self._manifest_json.get_path("/assets/integration") is not None
