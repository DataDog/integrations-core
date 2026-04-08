# (C) Datadog, Inc. 2024-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from pathlib import Path

import yaml

from ddev.cli.validate.all import VALIDATORS

REPO_ROOT = Path(__file__).resolve().parents[4]
WORKFLOW_PATH = REPO_ROOT / '.github' / 'workflows' / 'run-validations.yml'

# Inputs that are not validators
NON_VALIDATOR_INPUTS = frozenset({'repo', 'ddev-version'})


def _workflow_validator_names() -> set[str]:
    """Parse run-validations.yml and return the set of validation input names."""
    with WORKFLOW_PATH.open() as f:
        workflow = yaml.safe_load(f)

    # PyYAML parses the YAML key `on` as boolean True
    inputs = workflow[True]['workflow_call']['inputs']
    return {name for name in inputs if name not in NON_VALIDATOR_INPUTS}


def _registry_command_names() -> set[str]:
    """Return the set of Click command names from the VALIDATORS registry."""
    return {func.name for func, _, _ in VALIDATORS}


def test_validators_match_ci_workflow():
    """Every validation in run-validations.yml must have an entry in VALIDATORS, and vice versa."""
    workflow_names = _workflow_validator_names()
    registry_names = _registry_command_names()

    missing_from_registry = workflow_names - registry_names
    missing_from_workflow = registry_names - workflow_names

    errors = []
    if missing_from_registry:
        errors.append(f'Validations in CI but missing from VALIDATORS: {sorted(missing_from_registry)}')
    if missing_from_workflow:
        errors.append(f'Validations in VALIDATORS but missing from CI: {sorted(missing_from_workflow)}')

    assert not errors, '\n'.join(errors)
