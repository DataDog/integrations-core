import os
import yaml

from .compat import get_config


def get_profile_definition(profile):
    """
    Return the definition of an SNMP profile,
    either from the filesystem or from the profile configuration itself.

    Parameters:
    * profile (dict)

    Returns:
    * definition (dict)

    Raises:
    * Exception: if the definition file was not found or is malformed.
    """
    definition_file = profile.get('definition_file')

    if definition_file is not None:
        return _read_profile_definition(definition_file)

    return profile['definition']


def _read_profile_definition(definition_file):
    confd = get_config('confd_path')

    if not os.path.isabs(definition_file):
        definition_file = os.path.join(confd, 'snmp.d', 'profiles', definition_file)

    with open(definition_file) as f:
        return yaml.safe_load(f)
