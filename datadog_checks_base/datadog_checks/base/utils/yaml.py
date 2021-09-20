# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

import yaml

from ..ddyaml import pyyaml_load, pyyaml_load_all

log = logging.getLogger(__name__)


def yaml_load_force_loader(stream, Loader):
    """ Override the default monkey patch for this call """
    log.debug(
        "`%s` YAML loader is used instead of the default one, please make sure it is safe to do so", Loader.__name__
    )
    if pyyaml_load is None:
        return yaml.load(stream, Loader)
    return pyyaml_load(stream, Loader)


def yaml_load_all_force_loader(stream, Loader):
    """ Override the default monkey patch for this call """
    log.debug(
        "`%s` YAML loader is used instead of the default one, please make sure it is safe to do so", Loader.__name__
    )
    if pyyaml_load_all is None:
        return yaml.load_all(stream, Loader)
    return pyyaml_load_all(stream, Loader)
