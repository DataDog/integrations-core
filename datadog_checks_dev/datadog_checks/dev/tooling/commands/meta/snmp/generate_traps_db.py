# (C) Datadog, Inc. 2022-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)

import json
import os
from functools import lru_cache

import click
import yaml

from datadog_checks.dev import TempDir

from ...console import CONTEXT_SETTINGS, abort, echo_failure, echo_info, echo_success, echo_warning, set_debug
from .constants import CLEAR_LINE_ESCAPE_CODE, MIB_SOURCE_URL

# Unique identifiers of traps in json-compiled MIB files.
NOTIFICATION_TYPE = 'notificationtype'
ALLOWED_EXTENSIONS_BY_FORMAT = {"json": [".json"], "yaml": [".yml", ".yaml"]}


@click.command(
    context_settings=CONTEXT_SETTINGS,
    short_help='Generate a traps database that can be used by the '
    'Datadog Agent for resolving Traps OIDs to readable strings.',
)
@click.option(
    '--mib-sources',
    '-s',
    help='Url or a path to a directory containing the dependencies for [mib_files...].'
    'Traps defined in these files are ignored.',
)
@click.option(
    '--output-dir',
    '-o',
    help='Path to a directory where to store the created traps database file per MIB.'
    'Recommended option, do not use with --output-file',
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
)
@click.option(
    '--output-file',
    help='Path to a file to store a compacted version of the traps database file. Do not use with --output-dir',
    type=click.Path(exists=False, dir_okay=False, resolve_path=True),
)
@click.option(
    '--output-format',
    type=click.Choice(['yaml', 'json'], case_sensitive=False),
    default='yaml',
    help='Use json instead of yaml for the output file(s).',
)
@click.option(
    '--no-descr', help='Removes descriptions from the generated file(s) when set (more compact).', is_flag=True
)
@click.option('--debug', '-d', help='Include debug output', is_flag=True)
@click.argument('mib-files', nargs=-1, required=True, type=click.Path(exists=True, dir_okay=False, resolve_path=True))
def generate_traps_db(mib_sources, output_dir, output_file, output_format, no_descr, debug, mib_files):
    """Generate yaml or json formatted documents containing various information about traps. These files can be used by
    the Datadog Agent to enrich trap data.
    This command is intended for "Network Devices Monitoring" users who need to enrich traps that are not automatically
    supported by Datadog.

    The expected workflow is as such:\n
    1- Identify a type of device that is sending traps that Datadog does not already recognize.\n
    2- Fetch all the MIBs that Datadog does not support.\n
    3- Run `ddev meta snmp generate-traps-db -o ./output_dir/ /path/to/my/mib1 /path/to/my/mib2`\n

    You'll need to install pysmi manually beforehand.
    """
    from pysmi.codegen import JsonCodeGen
    from pysmi.compiler import MibCompiler
    from pysmi.parser import SmiV1CompatParser
    from pysmi.reader import getReadersFromUrls
    from pysmi.searcher import AnyFileSearcher
    from pysmi.writer import FileWriter

    if debug:
        set_debug()
        from pysmi import debug

        debug.setLogger(debug.Debug('all'))

    # Defaulting to github.com/DataDog/mibs.snmplabs.com/
    mib_sources = [mib_sources] if mib_sources else [MIB_SOURCE_URL]

    if output_file:
        allowed_extensions = ALLOWED_EXTENSIONS_BY_FORMAT[output_format]
        if not any(output_file.endswith(x) for x in allowed_extensions):
            abort(
                "Output file {} does not end with an allowed extension '{}'".format(
                    output_file, ", ".join(allowed_extensions)
                )
            )

    if output_dir and output_file:
        abort("Do not set both --output-dir and --output-file at the same time.")
    elif not output_file and not output_dir:
        abort("Need to set one of --output-dir or --output-file")

    with TempDir('ddev_mibs') as compiled_mibs_sources:
        compiled_mibs_sources = os.path.abspath(compiled_mibs_sources)
        echo_info("Writing intermediate compiled MIBs to {}".format(compiled_mibs_sources))

        mibs_sources_dir = os.path.join(compiled_mibs_sources, 'mibs_sources')
        if not os.path.isdir(mibs_sources_dir):
            os.mkdir(mibs_sources_dir)

        mib_sources = (
            sorted(set([os.path.abspath(os.path.dirname(x)) for x in mib_files if os.path.sep in x])) + mib_sources
        )

        mib_files = [os.path.basename(x) for x in mib_files]
        searchers = [AnyFileSearcher(compiled_mibs_sources).setOptions(exts=['.json'])]
        code_generator = JsonCodeGen()
        file_writer = FileWriter(compiled_mibs_sources).setOptions(suffix='.json')
        mib_compiler = MibCompiler(SmiV1CompatParser(tempdir=''), code_generator, file_writer)
        mib_compiler.addSources(*getReadersFromUrls(*mib_sources, **dict(fuzzyMatching=True)))
        mib_compiler.addSearchers(*searchers)

        compiled_mibs, compiled_dependencies_mibs = compile_and_report_status(mib_files, mib_compiler)

        # Move all the parent MIBs that had to be compiled but were not requested in the command to a subfolder.
        for mib_file_name in compiled_dependencies_mibs:
            os.replace(
                os.path.join(compiled_mibs_sources, mib_file_name + '.json'),
                os.path.join(mibs_sources_dir, mib_file_name + '.json'),
            )

        # Only generate trap_db with `mib_files` unless explicitly asked. Used to ignore other files that may be
        # present "compiled_mibs_sources"
        compiled_mibs = [os.path.join(compiled_mibs_sources, x + '.json') for x in compiled_mibs]

        # Generate the trap database based on the compiled MIBs.
        trap_db_per_mib = generate_trap_db(compiled_mibs, mibs_sources_dir, no_descr)

        use_json = output_format == "json"
        if output_file:
            # Compact representation, only one file
            write_compact_trap_db(trap_db_per_mib, output_file, use_json=use_json)
            echo_success("Wrote trap data to {}".format(os.path.abspath(output_file)))
        else:
            # Expanded representation, one file per MIB.
            write_trap_db_per_mib(trap_db_per_mib, output_dir, use_json=use_json)
            echo_success("Wrote trap data to {}".format(os.path.abspath(output_dir)))


def compile_and_report_status(mib_files, mib_compiler):
    """
    Iteratively compile all the mibs into multiple json files.
    :param mib_files: List of path to mib files to compile
    :param mib_compiler: A pysnmp compiler object
    :return: A list of the compiled MIBs and a list of dependant MIBs that had to be compiled as well.
    """
    child_compiled_mibs = []
    all_compiled_mibs = []  # Name of all compiled mibs including the parents recursively
    with click.progressbar(mib_files, label="Compiling MIBs: ", show_eta=False) as pb:
        for mib_file in pb:
            mibs_status = mib_compiler.compile(
                mib_file, noDeps=False, rebuild=True, dryRun=False, genTexts=True, writeMibs=True, ignoreErrors=False
            )
            failed_mibs = {k: v for k, v in mibs_status.items() if v == 'failed'}
            missing_mibs = [k for k, v in mibs_status.items() if v == 'missing']
            for mib_name, compilation_status in failed_mibs.items():
                echo_failure(
                    '{}Failed to compile MIB {}: {}'.format(CLEAR_LINE_ESCAPE_CODE, mib_name, compilation_status.error)
                )

            if missing_mibs:
                echo_failure('{}Missing MIBs: {}'.format(CLEAR_LINE_ESCAPE_CODE, ', '.join(missing_mibs)))

            compiled_mibs = {k: v for k, v in mibs_status.items() if v == 'compiled'}

            for mib_name, mib_status in compiled_mibs.items():
                all_compiled_mibs.append(mib_name)
                if mib_status.file == mib_file:
                    # Let's keep this file in the output directory
                    child_compiled_mibs.append(mib_name)

    # These MIBs were compiled but where not explicitly requested by the user. They will be moved
    # to a different folder.
    dependencies_only_mibs = set([x for x in all_compiled_mibs if x not in child_compiled_mibs])

    return child_compiled_mibs, dependencies_only_mibs


def write_trap_db_per_mib(trap_db_per_mib, output_dir, use_json=False):
    """
    Writes the generated traps database into multiple files, one per MIB.
    :param trap_db_per_mib: {<mib_name>: {"traps": {}, "vars": {}}} The traps database
    :param output_dir: The directory where to write the files.
    :param use_json: Whether to write a JSON or YAML file.
    """
    file_extension = '.json' if use_json else '.yml'
    for mib, trap_db in trap_db_per_mib.items():
        with open(os.path.join(output_dir, mib + file_extension), 'w') as output:
            if use_json:
                json.dump(trap_db, output, sort_keys=True)
            else:
                yaml.dump(trap_db, output, sort_keys=True)


def write_compact_trap_db(trap_db_per_mib, output_file, use_json=False):
    """
    Writes the generated traps database into a single compact file.
    :param trap_db_per_mib: {<mib_name>: {"traps": {}, "vars": {}}} The traps database
    :param output_file: Path to a file where to write the database.
    :param use_json: Whether to write a JSON or YAML file.
    """
    # All OIDs that are defined differently in multiple MIBs. Should very rarely happen but these
    # are ignored if any conflicts is found.
    conflict_oids = set()
    compact_db = {"traps": {}, "vars": {}, "mibs": []}
    for mib, trap_db in trap_db_per_mib.items():
        for trap_oid, trap in trap_db["traps"].items():
            if trap_oid in compact_db["traps"] and trap["name"] != compact_db["traps"][trap_oid]["name"]:
                echo_warning(
                    "Found name conflict for trap OID {}, ({} != {}). Will ignore".format(
                        trap_oid, trap['name'], compact_db["traps"][trap_oid]["name"]
                    )
                )
                conflict_oids.add(trap_oid)
            compact_db["traps"][trap_oid] = trap
        for var_oid, var in trap_db["vars"].items():
            if var_oid in compact_db["vars"] and var["name"] != compact_db["vars"][var_oid]["name"]:
                echo_warning(
                    "Found name conflict for variable OID {}, ({} != {}). Will ignore".format(
                        var_oid, var['name'], compact_db["vars"][var_oid]["name"]
                    )
                )
                conflict_oids.add(var_oid)
            compact_db["vars"][var_oid] = var
        compact_db['mibs'].append(mib)
    for oid in conflict_oids:
        if oid in compact_db["traps"]:
            del compact_db["traps"][oid]
        if oid in compact_db["vars"]:
            del compact_db["vars"]

    with open(output_file, 'w') as output:
        if use_json:
            json.dump(compact_db, output, sort_keys=True)
        else:
            yaml.dump(compact_db, output, sort_keys=True)


def generate_trap_db(compiled_mibs, compiled_mibs_sources, no_descr):
    """
    Generates the trap database from a list of mibs.
    :param compiled_mibs: List of path to json-compiled MIB files.
    :param compiled_mibs_sources: Path to a directory containing additional compiled MIB files for resolving deps.
    :return: {<mib_name>: {"traps": {}, "vars": {}}} The traps database
    """
    trap_db_per_mib = {}
    for compiled_mib_file in compiled_mibs:
        if not os.path.isfile(compiled_mib_file):
            continue
        with open(compiled_mib_file, 'r') as f:
            file_content = json.load(f)

        trap_db = {"traps": {}, "vars": {}}

        traps = {k: v for k, v in file_content.items() if v.get('class') == NOTIFICATION_TYPE}
        for trap in traps.values():
            try:
                trap_name = trap['name']
                trap_oid = trap['oid']
                trap_descr = trap.get('description', '')
                trap_db["traps"][trap_oid] = {"name": trap_name}
                if not no_descr:
                    trap_db["traps"][trap_oid]["descr"] = trap_descr
                for trap_var in trap.get('objects', []):
                    var_oid, var_descr = get_oid_and_descr(
                        trap_var['object'],
                        trap_var['module'],
                        search_locations=(os.path.dirname(compiled_mib_file), compiled_mibs_sources),
                    )
                    var_name = trap_var['object']
                    trap_db["vars"][var_oid] = {"name": var_name}
                    if not no_descr:
                        trap_db["vars"][var_oid]["descr"] = trap_descr
            except Exception as e:
                echo_info("Error in MIB {}: {}".format(compiled_mib_file, e))

        if trap_db['traps']:
            mib_name = file_content['meta']['module']
            trap_db_per_mib[mib_name] = trap_db

    return trap_db_per_mib


@lru_cache(maxsize=None)
def get_oid_and_descr(var_name, mib_name, search_locations=None):
    """
    Returns the oid and the description of a given variable and a MIB name.
    :param var_name: Name of the variable to search for
    :param mib_name: Name of the MIB defining the variable
    :param search_locations: Tuple of path to directories containing json-compiled MIB files
    :return: The oid and the description of the variable.
    """
    for location in search_locations:
        file_name = os.path.join(location, mib_name + '.json')
        if os.path.isfile(file_name):
            break
    else:
        raise Exception("Missing MIB {}".format(mib_name))

    with open(file_name, 'r') as f:
        file_content = json.load(f)
    return file_content[var_name]['oid'], file_content[var_name].get('description', '')
