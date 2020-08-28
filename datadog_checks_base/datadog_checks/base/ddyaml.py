# (C) Datadog, Inc. 2011-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import logging
from os.path import realpath

import yaml
from six import string_types

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
        stream_name = get_stream_name(stream)
        log.debug("Unsafe dumping of YAML has been disabled - using safe dumper instead in %s", stream_name)

    if pyyaml_dump_all:
        return pyyaml_dump_all(
            documents,
            stream,
            yDumper,
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
        yDumper,
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
        stream_name = get_stream_name(stream)
        log.debug("Unsafe loading of YAML has been disabled - using safe loader instead in %s", stream_name)

    if pyyaml_load:
        return pyyaml_load(stream, Loader=yLoader)

    return yaml.load(stream, Loader=yLoader)


def safe_yaml_load_all(stream, Loader=yLoader):
    if Loader != yLoader:
        stream_name = get_stream_name(stream)
        log.debug("Unsafe loading of YAML has been disabled - using safe loader instead in %s", stream_name)

    if pyyaml_load_all:
        return pyyaml_load_all(stream, Loader=yLoader)

    return yaml.load_all(stream, Loader=yLoader)


def get_stream_name(stream):
    """Using the same logic as pyyaml to handle both string types and file types. All file objects do not necessarily
    have a `name` attribute, in that case we can only say the stream is a file."""
    if isinstance(stream, string_types):
        return "<string>"
    elif hasattr(stream, 'name'):
        return realpath(stream.name)
    else:
        return "<file>"


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
