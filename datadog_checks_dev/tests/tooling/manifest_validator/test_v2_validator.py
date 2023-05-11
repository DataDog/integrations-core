# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import json
import os
from copy import deepcopy
from pathlib import Path

import mock
import pytest

import datadog_checks.dev.tooling.manifest_validator.common.validator as common
import datadog_checks.dev.tooling.manifest_validator.v2.validator as v2_validators
import tests.tooling.manifest_validator.input_constants as input_constants
from datadog_checks.dev.tooling.constants import get_root, set_root
from datadog_checks.dev.tooling.datastructures import JSONDict
from datadog_checks.dev.tooling.manifest_validator.constants import V2


# Helpers
def get_changed_immutable_short_name_manifest():
    """
    Helper function to change immutable short names in a manifest
    """
    immutable_attributes_changed_short_name = JSONDict(deepcopy(input_constants.V2_VALID_MANIFEST))
    immutable_attributes_changed_short_name['assets']['dashboards'] = {
        "oracle-changed": "assets/dashboards/example.json"
    }
    return immutable_attributes_changed_short_name


def get_changed_immutable_attribute_manifest():
    """
    Helper function to change other immutable attributes in a manifest
    """
    immutable_attributes_changed_attribute = JSONDict(deepcopy(input_constants.V2_VALID_MANIFEST))
    immutable_attributes_changed_attribute['app_id'] = 'datadog-oracle-changed'
    return immutable_attributes_changed_attribute


@pytest.fixture
def setup_route():
    # We want to change the path before and after running each individual test
    root = Path(os.path.realpath(__file__)).parent.parent.parent.parent.parent.absolute()
    current_root = get_root()
    set_root(str(root))
    yield root
    set_root(current_root)


def test_manifest_v2_maintainer_validator_incorrect_maintainer(setup_route):
    """
    Ensure MaintainerValidator fails if supplied an incorrect support_email
    """
    incorrect_maintainer_manifest = JSONDict(
        {
            "author": {
                "homepage": "https://www.datadoghq.com",
                "name": "Datadog",
                "sales_email": "help@datadoghq.com",
                "support_email": "fake_email@datadoghq.com",
            },
        }
    )

    # Use specific validator
    validator = common.MaintainerValidator(
        is_extras=False, is_marketplace=False, check_in_extras=False, check_in_marketplace=False, version=V2
    )
    validator.validate('active_directory', incorrect_maintainer_manifest, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_maintainer_validator_invalid_maintainer(setup_route):
    """
    Ensure MaintainerValidator fails if supplied a support_email with non-ASCII characters
    """
    invalid_maintainer_manifest = JSONDict(
        {
            "author": {
                "homepage": "https://www.datadoghq.com",
                "name": "Datadog",
                "sales_email": "help@datadoghq.com",
                "support_email": "Ǩ_help@datadoghq.com",
            },
        }
    )

    # Use specific validator
    validator = common.MaintainerValidator(
        is_extras=False, is_marketplace=False, check_in_extras=False, check_in_marketplace=False, version=V2
    )
    validator.validate('active_directory', invalid_maintainer_manifest, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_maintainer_validator_correct_maintainer(setup_route):
    # Use specific validator
    validator = common.MaintainerValidator(
        is_extras=False, is_marketplace=False, check_in_extras=False, check_in_marketplace=False, version=V2
    )
    validator.validate('active_directory', JSONDict(input_constants.V2_VALID_MANIFEST), False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_metrics_metadata_validator_file_exists_not_in_manifest(setup_route):
    """
    Ensure MetricsMetadataValidator fails if supplied an empty metadata_path value
    """
    file_exists_not_in_manifest = JSONDict(
        {
            "assets": {
                "integration": {
                    "metrics": {
                        "auto_install": True,
                        "check": "oracle.session_count",
                        "metadata_path": "",
                        "prefix": "oracle.",
                    },
                },
            },
        }
    )
    # Use specific validator
    validator = common.MetricsMetadataValidator(version=V2)
    validator.validate('active_directory', file_exists_not_in_manifest, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('os.path.isfile', return_value=False)
def test_manifest_v2_metrics_metadata_validator_file_in_manifest_not_exist(_, setup_route):
    """
    Ensure MetricsMetadataValidator fails if supplied a path to a non-existant metadata.csv
    """
    file_in_manifest_does_not_exist = JSONDict(
        {
            "assets": {
                "integration": {
                    "metrics": {
                        "auto_install": True,
                        "check": "oracle.session_count",
                        "metadata_path": "metrics_metadata1.csv",
                        "prefix": "oracle.",
                    },
                },
            },
        }
    )
    # Use specific validator
    validator = common.MetricsMetadataValidator(version=V2)
    validator.validate('active_directory', file_in_manifest_does_not_exist, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.utils.read_metadata_rows', return_value=input_constants.ORACLE_METADATA_CSV_EXAMPLE
)
def test_manifest_v2_metrics_metadata_validator_correct_metadata(_, setup_route):
    # Use specific validator
    validator = common.MetricsMetadataValidator(version=V2)
    validator.validate('active_directory', JSONDict(input_constants.V2_VALID_MANIFEST), False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_metrics_to_check_validator_check_not_in_metadata(setup_route):
    """
    Ensure MetricToCheckValidator fails if the check value is not present in
    the metadata.csv
    """
    check_not_in_metadata_csv = JSONDict(
        {
            "assets": {
                "integration": {
                    "metrics": {
                        "auto_install": True,
                        "check": "oracle.session_count",
                        "metadata_path": "metrics_metadata.csv",
                        "prefix": "oracle.",
                    },
                },
            },
        }
    )
    # Use specific validator
    validator = common.MetricToCheckValidator(version=V2)
    validator.validate('active_directory', check_not_in_metadata_csv, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_metrics_to_check_validator_check_not_in_manifest(setup_route):
    """
    Ensure MetricToCheckValidator fails if supplied an empty check value
    """
    check_not_in_manifest = JSONDict(
        {
            "assets": {
                "integration": {
                    "metrics": {
                        "auto_install": True,
                        "check": "",
                        "metadata_path": "metrics_metadata.csv",
                        "prefix": "oracle.",
                    },
                },
            },
        }
    )

    # Use specific validator
    validator = common.MetricToCheckValidator(version=V2)
    validator.validate('active_directory', check_not_in_manifest, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.utils.read_metadata_rows', return_value=input_constants.ORACLE_METADATA_CSV_EXAMPLE
)
def test_manifest_v2_metrics_metadata_validator_correct_check_in_metadata(_, setup_route):
    # Use specific validator
    validator = common.MetricToCheckValidator(version=V2)
    validator.validate('active_directory', JSONDict(input_constants.V2_VALID_MANIFEST), False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('datadog_checks.dev.tooling.utils.has_logs', return_value=True)
def test_manifest_v2_logs_category_validator_has_logs_no_tag(_, setup_route):
    """
    Ensure LogsCategoryValidator fails if the integration has logs but no Log Collection tag
    """
    has_logs_no_tag_manifest = JSONDict(
        {
            "classifier_tags": [
                "Category::Marketplace",
                "Offering::Integration",
                "Offering::UI Extension",
            ],
        }
    )

    # Use specific validator
    validator = common.LogsCategoryValidator(version=V2)
    validator.validate('active_directory', has_logs_no_tag_manifest, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('datadog_checks.dev.tooling.utils.has_logs', return_value=True)
def test_manifest_v2_logs_category_validator_correct_has_logs_correct_tag(_, setup_route):
    # Use specific validator
    validator = common.LogsCategoryValidator(version=V2)
    validator.validate('active_directory', JSONDict(input_constants.V2_VALID_MANIFEST), False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_display_on_public_validator_invalid(setup_route):
    """
    Ensure DisplayOnPublicValidator fails if the display_on_public_website attribute is not True
    """
    display_on_public_invalid_manifest = JSONDict({"app_id": "datadog-oracle"})

    # Use specific validator
    validator = v2_validators.DisplayOnPublicValidator(version=V2)
    validator.validate('active_directory', display_on_public_invalid_manifest, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_display_on_public_validator_valid(setup_route):
    display_on_public_valid_manifest = JSONDict({"display_on_public_website": True})

    # Use specific validator
    validator = v2_validators.DisplayOnPublicValidator(version=V2)
    validator.validate('active_directory', display_on_public_valid_manifest, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('requests.post', return_value=input_constants.MockedResponseInvalid())
def test_manifest_v2_schema_validator_manifest_invalid(_, setup_route):
    """
    Ensure SchemaValidator fails if a 400 status_code is received from request
    """
    # Use specific validator
    validator = v2_validators.SchemaValidator(ctx=input_constants.MockedContextObj(), version=V2, skip_if_errors=False)
    validator.validate('active_directory', JSONDict(input_constants.V2_VALID_MANIFEST), False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('requests.post', return_value=input_constants.MockedResponseValid())
def test_manifest_v2_schema_validator_manifest_valid(_, setup_route):
    # Use specific validator
    validator = v2_validators.SchemaValidator(ctx=input_constants.MockedContextObj(), version=V2, skip_if_errors=False)
    validator.validate('active_directory', JSONDict(input_constants.V2_VALID_MANIFEST), False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.manifest_validator.common.validator.git_show_file',
    return_value=json.dumps(input_constants.V2_VALID_MANIFEST),
)
def test_manifest_v2_immutable_attributes_validator_invalid_attribute_change(_, setup_route):
    """
    Ensure ImmutableAttributesValidator fails if an immutable attribute is changed
    """
    # Use specific validator
    validator = common.ImmutableAttributesValidator(version=V2)
    validator.validate('active_directory', JSONDict(get_changed_immutable_attribute_manifest()), False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.manifest_validator.common.validator.git_show_file',
    return_value=json.dumps(input_constants.V2_VALID_MANIFEST),
)
def test_manifest_v2_immutable_attributes_validator_invalid_short_name_change(_, setup_route):
    """
    Ensure ImmutableAttributesValidator fails if the short name of an asset is changed
    """
    # Use specific validator
    validator = common.ImmutableAttributesValidator(version=V2)
    validator.validate('active_directory', JSONDict(get_changed_immutable_short_name_manifest()), False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.manifest_validator.common.validator.git_show_file',
    return_value=input_constants.IMMUTABLE_ATTRIBUTES_V1_MANIFEST,
)
def test_manifest_v2_immutable_attributes_validator_version_upgrade(_, setup_route):
    """
    Ensure ImmutableAttributesValidator skips validations if the manifest is being upgraded from v1 to v2
    """
    # Use specific validator
    validator = common.ImmutableAttributesValidator(version=V2)
    validator.validate('active_directory', input_constants.IMMUTABLE_ATTRIBUTES_V2_MANIFEST, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.manifest_validator.common.validator.git_show_file',
    return_value=json.dumps(input_constants.V2_VALID_MANIFEST),
)
def test_manifest_v2_immutable_attributes_validator_valid_change(_, setup_route):
    # Use specific validator
    validator = common.ImmutableAttributesValidator(version=V2)
    validator.validate('active_directory', JSONDict(input_constants.V2_VALID_MANIFEST), False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('os.path.getsize', return_value=300000)
def test_manifest_v2_media_gallery_validator_pass(_, setup_route):
    # Use specific validator
    validator = v2_validators.MediaGalleryValidator(is_marketplace=True, version=V2, check_in_extras=False)
    validator.validate('active_directory', JSONDict(input_constants.VALID_MEDIA_MANIFEST), False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('os.path.getsize', return_value=1300000)
def test_manifest_v2_media_gallery_validator_image_size_too_large(_, setup_route):
    # Use specific validator
    validator = v2_validators.MediaGalleryValidator(is_marketplace=True, version=V2, check_in_extras=False)
    validator.validate('active_directory', JSONDict(input_constants.VALID_MEDIA_MANIFEST), False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('os.path.getsize', return_value=300000)
def test_manifest_v2_media_gallery_validator_too_many_videos(_, setup_route):
    # Use specific validator
    validator = v2_validators.MediaGalleryValidator(is_marketplace=True, version=V2, check_in_extras=False)
    validator.validate('active_directory', JSONDict(input_constants.INVALID_MEDIA_MANIFEST_TOO_MANY_VIDEOS), False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('os.path.getsize', return_value=300000)
def test_manifest_v2_media_gallery_validator_bad_structure(_, setup_route):
    # Use specific validator
    validator = v2_validators.MediaGalleryValidator(is_marketplace=True, version=V2, check_in_extras=False)
    validator.validate('active_directory', JSONDict(input_constants.INVALID_MEDIA_MANIFEST_BAD_STRUCTURE), False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('os.path.getsize', return_value=300000)
def test_manifest_v2_media_gallery_validator_incorrect_vimeo_id_type(_, setup_route):
    # Use specific validator
    validator = v2_validators.MediaGalleryValidator(is_marketplace=True, version=V2, check_in_extras=False)
    validator.validate(
        'active_directory', JSONDict(input_constants.INVALID_MEDIA_MANIFEST_INCORRECT_VIMEO_ID_TYPE), False
    )

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_tile_description_validator_pass(setup_route):
    # Use specific validator
    validator = v2_validators.TileDescriptionValidator(is_marketplace=True, version=V2, check_in_extras=True)
    validator.validate('active_directory', input_constants.VALID_TILE_DESCRIPTION_V2_MANIFEST, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_tile_description_validator_invalid(setup_route):
    # Use specific validator
    validator = v2_validators.TileDescriptionValidator(is_marketplace=True, version=V2, check_in_extras=True)
    validator.validate('active_directory', input_constants.INVALID_TILE_DESCRIPTION_V2_MANIFEST, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_changelog_found(setup_route):
    manifest = JSONDict(
        {
            "tile": {
                "changelog": "CHANGELOG.md",
            },
        }
    )

    validator = v2_validators.ChangelogValidator(version=V2)
    validator.validate('datadog_checks_dev', manifest, False)

    assert not validator.result.failed


def test_manifest_v2_changelog_not_found(setup_route):
    manifest = JSONDict(
        {
            "tile": {
                "changelog": "CHANGELOG_NOT_FOUND.md",
            },
        }
    )

    validator = v2_validators.ChangelogValidator(version=V2)
    validator.validate('datadog_checks_dev', manifest, False)

    assert validator.result.failed


def test_manifest_v2_changelog_case_sensitive(setup_route):
    manifest = JSONDict(
        {
            "tile": {
                "changelog": "CHANGELOG.MD",
            },
        }
    )

    validator = v2_validators.ChangelogValidator(version=V2)
    validator.validate('datadog_checks_dev', manifest, False)

    assert validator.result.failed
