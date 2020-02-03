# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
"""
Utilities and helpers related to SNMP profiles.
"""

import os
from typing import Any, Dict

import yaml

from ..compat import get_config


def get_profile_definition(profile):
    # type: (Dict[str, Any]) -> Dict[str, Any]
    """
    Return the definition of an SNMP profile,
    either from the filesystem or from the profile configuration itself.

    Raises:
    * Exception: if the definition file was not found or is malformed.
    """
    definition_file = profile.get('definition_file')

    if definition_file is not None:
        return _read_profile_definition(definition_file)

    return profile['definition']


def _read_profile_definition(definition_file):
    # type: (str) -> Dict[str, Any]
    confd = get_config('confd_path')

    if not os.path.isabs(definition_file):
        definition_file = os.path.join(confd, 'snmp.d', 'profiles', definition_file)

    with open(definition_file) as f:
        return yaml.safe_load(f)
