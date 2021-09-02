# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import yaml

from ..ddyaml import pyyaml_load, pyyaml_load_all


def yaml_load_force_loader(stream, Loader):
    """ Override the default monkey patch for this call """
    if pyyaml_load is None:
        return yaml.load(stream, Loader)
    return pyyaml_load(stream, Loader)


def yaml_load_all_force_loader(stream, Loader):
    """ Override the default monkey patch for this call """
    if pyyaml_load_all is None:
        return yaml.load_all(stream, Loader)
    return pyyaml_load_all(stream, Loader)
