# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import os
from pathlib import Path

import mock
import pytest
import tests.tooling.manifest_validator.input_constants as input_constants

import datadog_checks.dev.tooling.manifest_validator.common.validator as common
import datadog_checks.dev.tooling.manifest_validator.v2.validator as v2_validators
from datadog_checks.dev.tooling.constants import get_root, set_root
from datadog_checks.dev.tooling.manifest_validator import get_all_validators
from datadog_checks.dev.tooling.manifest_validator.constants import V2


@pytest.fixture
def setup_route():
    # We want to change the path before and after running each individual test
    root = Path(os.path.realpath(__file__)).parent.parent.parent.parent.parent.absolute()
    current_root = get_root()
    set_root(str(root))
    yield root
    set_root(current_root)


@mock.patch(
    'datadog_checks.dev.tooling.utils.read_metadata_rows', return_value=input_constants.ORACLE_METADATA_CSV_EXAMPLE
)
def test_manifest_v2_all_pass(_, setup_route):
    validators = get_all_validators(False, "2.0.0")
    for validator in validators:
        # Currently skipping SchemaValidator because of no context object and config
        if isinstance(validator, v2_validators.SchemaValidator):
            continue

        validator.validate('active_directory', input_constants.V2_MANIFEST_ALL_PASS, False)
        assert not validator.result.failed, validator.result
        assert not validator.result.fixed


def test_manifest_v2_maintainer_validator_incorrect_maintainer(setup_route):
    # Use specific validator
    validator = common.MaintainerValidator(
        is_extras=False, is_marketplace=False, check_in_extras=False, check_in_marketplace=False, version=V2
    )
    validator.validate('active_directory', input_constants.INCORRECT_MAINTAINER_MANIFEST, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_maintainer_validator_invalid_maintainer(setup_route):
    # Use specific validator
    validator = common.MaintainerValidator(
        is_extras=False, is_marketplace=False, check_in_extras=False, check_in_marketplace=False, version=V2
    )
    validator.validate('active_directory', input_constants.INVALID_MAINTAINER_MANIFEST, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_maintainer_validator_correct_maintainer(setup_route):
    # Use specific validator
    validator = common.MaintainerValidator(
        is_extras=False, is_marketplace=False, check_in_extras=False, check_in_marketplace=False, version=V2
    )
    validator.validate('active_directory', input_constants.CORRECT_MAINTAINER_MANIFEST, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_metrics_metadata_validator_file_exists_not_in_manifest(setup_route):
    # Use specific validator
    validator = common.MetricsMetadataValidator(version=V2)
    validator.validate('active_directory', input_constants.FILE_EXISTS_NOT_IN_MANIFEST, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('os.path.isfile', return_value=False)
def test_manifest_v2_metrics_metadata_validator_file_in_manifest_not_exist(_, setup_route):
    # Use specific validator
    validator = common.MetricsMetadataValidator(version=V2)
    validator.validate('active_directory', input_constants.FILE_IN_MANIFEST_DOES_NOT_EXIST, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.utils.read_metadata_rows', return_value=input_constants.ORACLE_METADATA_CSV_EXAMPLE
)
def test_manifest_v2_metrics_metadata_validator_correct_metadata(_, setup_route):
    # Use specific validator
    validator = common.MetricsMetadataValidator(version=V2)
    validator.validate('active_directory', input_constants.CORRECT_METADATA_FILE_MANIFEST, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_metrics_to_check_validator_check_not_in_metadata(setup_route):
    # Use specific validator
    validator = common.MetricToCheckValidator(version=V2)
    validator.validate('active_directory', input_constants.CHECK_NOT_IN_METADATA_MANIFEST, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_metrics_to_check_validator_check_not_in_manifest(setup_route):
    # Use specific validator
    validator = common.MetricToCheckValidator(version=V2)
    validator.validate('active_directory', input_constants.CHECK_NOT_IN_MANIFEST, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.utils.read_metadata_rows', return_value=input_constants.ORACLE_METADATA_CSV_EXAMPLE
)
def test_manifest_v2_metrics_metadata_validator_correct_check_in_metadata(_, setup_route):
    # Use specific validator
    validator = common.MetricToCheckValidator(version=V2)
    validator.validate('active_directory', input_constants.CORRECT_CHECK_IN_METADATA_MANIFEST, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('datadog_checks.dev.tooling.utils.has_logs', return_value=True)
def test_manifest_v2_logs_category_validator_has_logs_no_tag(_, setup_route):
    # Use specific validator
    validator = common.LogsCategoryValidator(version=V2)
    validator.validate('active_directory', input_constants.HAS_LOGS_NO_TAG_MANIFEST, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('datadog_checks.dev.tooling.utils.has_logs', return_value=True)
def test_manifest_v2_logs_category_validator_correct_has_logs_correct_tag(_, setup_route):
    # Use specific validator
    validator = common.LogsCategoryValidator(version=V2)
    validator.validate('active_directory', input_constants.V2_MANIFEST_ALL_PASS, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_display_on_public_validator_invalid(setup_route):
    # Use specific validator
    validator = v2_validators.DisplayOnPublicValidator(version=V2)
    validator.validate('active_directory', input_constants.DISPLAY_ON_PUBLIC_INVALID_MANIFEST, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


def test_manifest_v2_display_on_public_validator_valid(setup_route):
    # Use specific validator
    validator = v2_validators.DisplayOnPublicValidator(version=V2)
    validator.validate('active_directory', input_constants.DISPLAY_ON_PUBLIC_VALID_MANIFEST, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('requests.post', return_value=input_constants.MockedResponseInvalid())
def test_manifest_v2_schema_validator_manifest_invalid(_, setup_route):
    # Use specific validator
    validator = v2_validators.SchemaValidator(ctx=input_constants.MockedContextObj(), version=V2, skip_if_errors=False)
    validator.validate('active_directory', input_constants.V2_MANIFEST_ALL_PASS, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch('requests.post', return_value=input_constants.MockedResponseValid())
def test_manifest_v2_schema_validator_manifest_valid(_, setup_route):
    # Use specific validator
    validator = v2_validators.SchemaValidator(ctx=input_constants.MockedContextObj(), version=V2, skip_if_errors=False)
    validator.validate('active_directory', input_constants.V2_MANIFEST_ALL_PASS, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.manifest_validator.common.validator.git_show_file',
    return_value=input_constants.IMMUTABLE_ATTRIBUTES_PREV_MANIFEST_INVALID,
)
def test_manifest_v2_immutable_attributes_validator_invalid_attribute_change(_, setup_route):
    # Use specific validator
    validator = common.ImmutableAttributesValidator(version=V2)
    validator.validate('active_directory', input_constants.IMMUTABLE_ATTRIBUTES_CURRENT_MANIFEST_INVALID, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.manifest_validator.common.validator.git_show_file',
    return_value=input_constants.IMMUTABLE_ATTRIBUTES_PREV_MANIFEST_INVALID,
)
def test_manifest_v2_immutable_attributes_validator_invalid_short_name_change(_, setup_route):
    # Use specific validator
    validator = common.ImmutableAttributesValidator(version=V2)
    validator.validate('active_directory', input_constants.IMMUTABLE_ATTRIBUTES_CUR_MANIFEST_INVALID_SHORT_NAME, False)

    # Assert test case
    assert validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.manifest_validator.common.validator.git_show_file',
    return_value=input_constants.IMMUTABLE_ATTRIBUTES_V1_MANIFEST,
)
def test_manifest_v2_immutable_attributes_validator_version_upgrade(_, setup_route):
    # Use specific validator
    validator = common.ImmutableAttributesValidator(version=V2)
    validator.validate('active_directory', input_constants.IMMUTABLE_ATTRIBUTES_V2_MANIFEST, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed


@mock.patch(
    'datadog_checks.dev.tooling.manifest_validator.common.validator.git_show_file',
    return_value=input_constants.IMMUTABLE_ATTRIBUTES_PREV_MANIFEST_INVALID,
)
def test_manifest_v2_immutable_attributes_validator_valid_change(_, setup_route):
    # Use specific validator
    validator = common.ImmutableAttributesValidator(version=V2)
    validator.validate('active_directory', input_constants.IMMUTABLE_ATTRIBUTES_CURRENT_MANIFEST_VALID, False)

    # Assert test case
    assert not validator.result.failed, validator.result
    assert not validator.result.fixed
