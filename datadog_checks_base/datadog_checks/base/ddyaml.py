# (C) Datadog, Inc. 2011-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging

import yaml

try:
    from yaml import CSafeDumper as yDumper
    from yaml import CSafeLoader as yLoader
except ImportError:
    # On source install C Extensions might have not been built
    from yaml import SafeDumper as yDumper  # noqa, imported from here elsewhere
    from yaml import SafeLoader as yLoader  # noqa, imported from here elsewhere

log = logging.getLogger(__name__)

pyyaml_load = None
pyyaml_load_all = None
pyyaml_dump_all = None


def safe_yaml_dump_all(
    documents,
    stream=None,
    Dumper=yDumper,
    default_style=None,
    default_flow_style=None,
    canonical=None,
    indent=None,
    width=None,
    allow_unicode=None,
    line_break=None,
    encoding='utf-8',
    explicit_start=None,
    explicit_end=None,
    version=None,
    tags=None,
):
    if Dumper != yDumper:
        log.debug(
            "`%s` YAML dumper is used instead of the default one, please make sure it is safe to do so", Dumper.__name__
        )

    if pyyaml_dump_all:
        return pyyaml_dump_all(
            documents,
            stream,
            Dumper,
            default_style,
            default_flow_style,
            canonical,
            indent,
            width,
            allow_unicode,
            line_break,
            encoding,
            explicit_start,
            explicit_end,
            version,
            tags,
        )

    return yaml.dump_all(
        documents,
        stream,
        Dumper,
        default_style,
        default_flow_style,
        canonical,
        indent,
        width,
        allow_unicode,
        line_break,
        encoding,
        explicit_start,
        explicit_end,
        version,
        tags,
    )


def safe_yaml_load(stream, Loader=yLoader):
    if Loader != yLoader:
        log.debug(
            "`%s` YAML loader is used instead of the default one, please make sure it is safe to do so", Loader.__name__
        )

    if pyyaml_load:
        return pyyaml_load(stream, Loader=Loader)

    return yaml.load(stream, Loader=Loader)


def safe_yaml_load_all(stream, Loader=yLoader):
    if Loader != yLoader:
        log.debug(
            "`%s` YAML loader is used instead of the default one, please make sure it is safe to do so", Loader.__name__
        )

    if pyyaml_load_all:
        return pyyaml_load_all(stream, Loader=Loader)

    return yaml.load_all(stream, Loader=Loader)


def monkey_patch_pyyaml():
    global pyyaml_load
    global pyyaml_load_all
    global pyyaml_dump_all

    if not pyyaml_load:
        log.info("monkey patching yaml.load...")
        pyyaml_load = yaml.load
        yaml.load = safe_yaml_load
    if not pyyaml_load_all:
        log.info("monkey patching yaml.load_all...")
        pyyaml_load_all = yaml.load_all
        yaml.load_all = safe_yaml_load_all
    if not pyyaml_dump_all:
        log.info("monkey patching yaml.dump_all... (affects all yaml dump operations)")
        pyyaml_dump_all = yaml.dump_all
        yaml.dump_all = safe_yaml_dump_all


def monkey_patch_pyyaml_reverse():
    global pyyaml_load
    global pyyaml_load_all
    global pyyaml_dump_all

    if pyyaml_load:
        log.info("reversing monkey patch for yaml.load...")
        yaml.load = pyyaml_load
        pyyaml_load = None
    if pyyaml_load_all:
        log.info("reversing monkey patch for yaml.load_all...")
        yaml.load_all = pyyaml_load_all
        pyyaml_load_all = None
    if pyyaml_dump_all:
        log.info("reversing monkey patch for yaml.dump_all... (affects all yaml dump operations)")
        yaml.dump_all = pyyaml_dump_all
        pyyaml_dump_all = None
