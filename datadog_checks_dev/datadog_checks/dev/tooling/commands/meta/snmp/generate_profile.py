# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import json
import os
from collections import namedtuple
from tempfile import gettempdir

import click
import yaml

from ...console import CONTEXT_SETTINGS, abort, echo_debug, echo_info, set_debug
from .constants import MIB_COMPILED_URL, MIB_SOURCE_URL


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Generate an SNMP profile from a collection of MIB files')
@click.argument('mib_files', nargs=-1)
@click.option('-f', '--filters', help='Path to OIDs filter', default=None)
@click.option('-a', '--aliases', help='Path to metric tag aliases', default=None)
@click.option('--debug', '-d', help='Include debug output', is_flag=True)
@click.option('--interactive', '-i', help='Prompt to confirm before saving to a file', is_flag=True)
@click.option(
    '--source',
    '-s',
    help='Source of the MIBs files. Can be a url or a path for a directory',
    default=MIB_SOURCE_URL,
)
@click.option(
    '--compiled_mibs_path',
    '-c',
    help='Source of compiled MIBs files. Can be a url or a path for a directory',
    default=MIB_COMPILED_URL,
)
@click.pass_context
def generate_profile_from_mibs(ctx, mib_files, filters, aliases, debug, interactive, source, compiled_mibs_path):
    """
    Generate an SNMP profile from MIBs. Accepts a directory path containing mib files
    to be used as source to generate the profile, along with a filter if a device or
    family of devices support only a subset of oids from a mib.

    filters is the path to a yaml file containing a collection of MIBs, with their list of
    MIB node names to be included. For example:
    ```yaml
    RFC1213-MIB:
    - system
    - interfaces
    - ip
    CISCO-SYSLOG-MIB: []
    SNMP-FRAMEWORK-MIB:
    - snmpEngine
    ```
    Note that each `MIB:node_name` correspond to exactly one and only one OID. However, some MIBs report legacy nodes
    that are overwritten.

    To resolve, edit the MIB by removing legacy values manually before loading them with this profile generator. If a
    MIB is fully supported, it can be omitted from the filter as MIBs not found in a filter will be fully loaded.
    If a MIB is *not* fully supported, it can be listed with an empty node list, as `CISCO-SYSLOG-MIB` in the example.

    `-a, --aliases` is an option to provide the path to a YAML file containing a list of aliases to be
    used as metric tags for tables, in the following format:
    ```yaml
    aliases:
    - from:
        MIB: ENTITY-MIB
        name: entPhysicalIndex
      to:
        MIB: ENTITY-MIB
        name: entPhysicalName
    ```
    MIBs tables most of the time define a column OID within the table, or from a different table and even different MIB,
    which value can be used to index entries. This is the `INDEX` field in row nodes. As an example,
    entPhysicalContainsTable in ENTITY-MIB
    ```txt
    entPhysicalContainsEntry OBJECT-TYPE
    SYNTAX      EntPhysicalContainsEntry
    MAX-ACCESS  not-accessible
    STATUS      current
    DESCRIPTION
            "A single container/'containee' relationship."
    INDEX       { entPhysicalIndex, entPhysicalChildIndex }
    ::= { entPhysicalContainsTable 1 }
    ```
    or its json dump, where `INDEX` is replaced by indices
    ```json
    "entPhysicalContainsEntry": {
        "name": "entPhysicalContainsEntry",
        "oid": "1.3.6.1.2.1.47.1.3.3.1",
        "nodetype": "row",
        "class": "objecttype",
        "maxaccess": "not-accessible",
        "indices": [
          {
            "module": "ENTITY-MIB",
            "object": "entPhysicalIndex",
            "implied": 0
          },
          {
            "module": "ENTITY-MIB",
            "object": "entPhysicalChildIndex",
            "implied": 0
          }
        ],
        "status": "current",
        "description": "A single container/'containee' relationship."
      },
    ```
    Sometimes indexes are columns from another table, and we might want to use another column as it could have more
    human readable information - we might prefer to see the interface name vs its numerical table index. This can be
    achieved using metric_tag_aliases

    Return a list of SNMP metrics and copy its yaml dump to the clipboard
    Metric tags need to be added manually
    """
    if debug:
        set_debug()
        from pysmi import debug

        debug.setLogger(debug.Debug('all'))

    # ensure at least one mib file is provided
    if len(mib_files) == 0:
        abort('🙄 no mib file provided, need at least one mib file to generate a profile')

    # create a list of all mib files directories and mib names
    source_directories = set()
    mibs = set()
    for file in mib_files:
        source_directories.add(os.path.dirname(file))
        mibs.add(os.path.splitext(os.path.basename(file))[0])
    # create a tmp dir for compiled json mibs
    json_destination_directory = os.path.join(gettempdir(), 'mibs')

    if not os.path.exists(json_destination_directory):
        os.mkdir(json_destination_directory)

    profile_oid_collection = {}
    # build profile
    for oid_node in _extract_oids_from_mibs(
        list(mibs), list(source_directories), json_destination_directory, source, compiled_mibs_path, filters
    ):
        if oid_node.node_type == 'table':
            _add_profile_table_node(profile_oid_collection, oid_node)
        elif oid_node.node_type == 'row':
            # requires
            _add_profile_row_node(
                profile_oid_collection,
                oid_node,
                os.path.dirname(mib_files[0]),
                metric_tag_aliases_path=aliases,
                json_mib_directory=json_destination_directory,
                source=source,
                compiled_mibs_path=compiled_mibs_path,
            )
        elif oid_node.node_type == 'column':
            _add_profile_column_node(profile_oid_collection, oid_node)
        elif oid_node.node_type == 'scalar':
            _add_profile_scalar_node(profile_oid_collection, oid_node)

    echo_info('{} metrics found'.format(len(profile_oid_collection.values())))
    yaml_data = yaml.dump({'metrics': list(profile_oid_collection.values())}, sort_keys=False)
    if not interactive or click.confirm('Save to file?'):
        output_filename = 'metrics.yaml'
        with open(output_filename, 'w') as f:
            f.write(yaml_data)
            echo_info('Metrics saved to {}'.format(output_filename))

    echo_debug(yaml.dump({'metrics': list(profile_oid_collection.values())}, sort_keys=False))


class OidNodeInvalid(Exception):
    """Missing OID, name or class in oid node"""

    pass


OidTableIndex = namedtuple('OidIndex', ['index_module', 'index_name'])

JSON_NODE_PROP_CLASS = 'class'
JSON_NODE_PROP_DESCRIPTION = 'description'
JSON_NODE_PROP_INDICES = 'indices'
JSON_NODE_PROP_MAX_ACCESS = 'maxaccess'
JSON_NODE_PROP_MIB = 'mib'
JSON_NODE_PROP_NAME = 'name'
JSON_NODE_PROP_NODE_TYPE = 'nodetype'
JSON_NODE_PROP_OID = 'oid'

JSON_NODE_INDEX_NODE_PROP_MODULE = 'module'
JSON_NODE_INDEX_NODE_PROP_OBJECT = 'object'


class OidNode:
    def __init__(self, mib, mib_json_node):
        """
        Creates an oid node from a mib and a mib json node

        Example of mib json node:
        ```json
        {
            "name": "mIBMinorVersionNumber",
            "oid": "1.3.6.1.4.1.674.10892.1.1.2",
            "nodetype": "scalar",
            "class": "objecttype",
            "syntax": {
              "type": "DellUnsigned8BitRange",
              "class": "type"
            },
            "maxaccess": "read-only",
            "status": "mandatory",
            "description":
            "0001.0002 This attribute defines the minor version number of the Dell Enterprise Server Group MIB ."
        }
        ```
        """
        expected_json_node_props = [JSON_NODE_PROP_OID, JSON_NODE_PROP_NAME, JSON_NODE_PROP_CLASS]
        if not all(json_prop in mib_json_node for json_prop in expected_json_node_props):
            raise OidNodeInvalid

        self.mib_class = mib_json_node[JSON_NODE_PROP_CLASS]

        # The OBJECT-TYPE is defined by SNMP v1 and is used as a container for
        # storing information about the managed device, or some measured value on the device.
        # More details:
        # https://www.ibm.com/support/knowledgecenter/en/SSSHTQ_8.1.0/com.ibm.netcool_OMNIbus.doc_8.1.0/omnibus/wip/ua_mibmgr/reference/omn_ref_mib_mibobjects.html
        if not self.is_object:
            return

        self.name = mib_json_node[JSON_NODE_PROP_NAME]
        self.oid = mib_json_node[JSON_NODE_PROP_OID]
        self.mib = mib

        self.max_access = None
        if JSON_NODE_PROP_MAX_ACCESS in mib_json_node:
            self.max_access = mib_json_node[JSON_NODE_PROP_MAX_ACCESS]

        self.node_type = None
        if JSON_NODE_PROP_NODE_TYPE in mib_json_node:
            self.node_type = mib_json_node[JSON_NODE_PROP_NODE_TYPE]

        self.description = None
        if JSON_NODE_PROP_DESCRIPTION in mib_json_node:
            self.description = mib_json_node[JSON_NODE_PROP_DESCRIPTION]

        self.indices = None
        if JSON_NODE_PROP_INDICES in mib_json_node:
            indices = mib_json_node[JSON_NODE_PROP_INDICES]
            self.indices = []
            for item in indices:
                module = item[JSON_NODE_INDEX_NODE_PROP_MODULE]
                obj = item[JSON_NODE_INDEX_NODE_PROP_OBJECT]
                self.indices.append(OidTableIndex(index_module=module, index_name=obj))

    LEAVE_NODE_TYPES = {'table', 'row', 'column', 'scalar'}

    @property
    def is_middle_node(self):
        return self.node_type not in self.LEAVE_NODE_TYPES

    @property
    def is_unknown_type(self):
        return self.node_type is None

    @property
    def is_object(self):
        return self.mib_class == 'objecttype'


def _compile_mib_to_json(mib, source_mib_directories, destination_directory, source, compiled_mibs_path):
    from pysmi.borrower import AnyFileBorrower
    from pysmi.codegen import JsonCodeGen
    from pysmi.compiler import MibCompiler
    from pysmi.parser import SmiV1CompatParser
    from pysmi.reader import getReadersFromUrls
    from pysmi.searcher import AnyFileSearcher, StubSearcher
    from pysmi.writer import FileWriter

    mib_stubs = JsonCodeGen.baseMibs

    compile_documentation = True

    # Compiler infrastructure

    code_generator = JsonCodeGen()

    file_writer = FileWriter(destination_directory).setOptions(suffix='.json')

    mib_compiler = MibCompiler(SmiV1CompatParser(tempdir=''), code_generator, file_writer)

    # use source_mib_directories as mibs source
    sources = [source]
    sources.extend(source_mib_directories)
    mib_compiler.addSources(*getReadersFromUrls(*sources, **dict(fuzzyMatching=True)))

    searchers = [AnyFileSearcher(destination_directory).setOptions(exts=['.json']), StubSearcher(*mib_stubs)]
    mib_compiler.addSearchers(*searchers)

    # borrowers, aka compiled mibs source
    borrowers = [
        AnyFileBorrower(borrower_reader, genTexts=True).setOptions(exts=['.json'])
        for borrower_reader in getReadersFromUrls(*[compiled_mibs_path], **dict(lowcaseMatching=False))
    ]
    mib_compiler.addBorrowers(borrowers)

    processed = mib_compiler.compile(
        mib,
        **dict(
            noDeps=False,
            rebuild=False,
            dryRun=False,
            dstTemplate=None,
            genTexts=compile_documentation,
            textFilter=False and (lambda symbol, text: text) or None,
            writeMibs=True,
            ignoreErrors=False,
        )
    )

    return processed


def _get_reader_from_source(source):
    from pysmi.reader.localfile import FileReader

    if os.path.exists(source):
        return FileReader(source)
    return _get_reader_from_url(source)


def _get_reader_from_url(url):
    from urllib.parse import urlparse

    from pysmi.reader.httpclient import HttpReader

    if not (url.startswith('//') or url.startswith('http://') or url.startswith('https://')):
        url = "//" + url
    url_parsed = urlparse(url)
    url_host = url_parsed.hostname
    url_locationTemplate = url_parsed.path
    port = 80
    if url_parsed.port:
        port = url_parsed.port
    return HttpReader(url_host, port, url_locationTemplate)


def _load_json_module(source_directory, mib):
    try:
        with open(os.path.join(source_directory, mib + '.json')) as mib_json:
            return json.load(mib_json)
    except FileNotFoundError:
        return None


def _load_module_or_compile(mib, source_directories, json_mib_directory, source, compiled_mibs_path):
    # try loading the json mib, if already compiled
    echo_debug('⏳ Loading mib {}'.format(mib))
    mib_json = _load_json_module(json_mib_directory, mib)
    if mib_json is not None:
        echo_debug('✅ Mib {} loaded'.format(mib))
        return mib_json

    # compile and reload
    echo_debug('⏳ Compile mib {}'.format(mib))
    processed = _compile_mib_to_json(mib, source_directories, json_mib_directory, source, compiled_mibs_path)
    echo_debug('✅ Mib {} compiled: {}'.format(mib, processed[mib]))
    if processed[mib] != 'missing':
        mib_json = _load_json_module(json_mib_directory, mib)
        return mib_json

    return None


def _find_oid_by_name(mib, oid_name, source_directories, json_mib_directory, source, compiled_mibs_path):
    mib_json = _load_module_or_compile(mib, source_directories, json_mib_directory, source, compiled_mibs_path)
    if mib_json is None:
        return None

    if oid_name not in mib_json:
        return None

    return mib_json[oid_name]['oid']


def _find_name_by_oid(mib, oid, source_directories, json_mib_directory, source, compiled_mibs_path):
    mib_json = _load_module_or_compile(mib, source_directories, json_mib_directory, source, compiled_mibs_path)
    if mib_json is None:
        return None

    for oid_name in mib_json:
        if JSON_NODE_PROP_OID in mib_json[oid_name] and mib_json[oid_name][JSON_NODE_PROP_OID] == oid:
            return oid_name

    return None


def _filter_mib_oids(mib, json_mib, filter_data):
    # skip filtering if no filter is provided for this mib
    if filter_data is None or mib not in filter_data:
        return json_mib

    filtered_json_oids = {}
    for filter_oid_name in filter_data[mib]:
        # recursively add oids under filter_oid_name
        if filter_oid_name not in json_mib:
            continue

        # add only oids under filter_oid
        # Example
        # root_node_oid = 1.2.3.4.5
        # node[JSON_NODE_PROP_OID] = 1.2.3.4.5.6.2
        # => node is added to filtered_oids
        # node[JSON_NODE_PROP_OID] = 1.2.3.6.3.2
        # => node is excluded from  filtered_oids
        root_node = json_mib[filter_oid_name]
        root_node_oid = root_node[JSON_NODE_PROP_OID]
        filtered_oids = {
            node_name: node
            for (node_name, node) in json_mib.items()
            if JSON_NODE_PROP_OID in node and root_node_oid in node[JSON_NODE_PROP_OID]
        }
        filtered_json_oids.update(filtered_oids)

    return filtered_json_oids


def _extract_oids_from_mibs(
    mibs, source_directories, json_destination_directory, source, compiled_mibs_path, filter_path=None
):
    filter_data = None
    if filter_path is not None and os.path.isfile(filter_path):
        with open(filter_path) as f:
            filter_data = yaml.safe_load(f)

    json_mibs = {}
    for mib in mibs:
        json_mib = _load_module_or_compile(
            mib, source_directories, json_destination_directory, source, compiled_mibs_path
        )
        if json_mib is None:
            continue

        # apply filter
        filtered_json_mib = _filter_mib_oids(mib, json_mib, filter_data)
        json_mibs[mib] = filtered_json_mib

    oid_list = []
    for mib, json_mib in json_mibs.items():
        for key in json_mib:
            try:
                oid_node = OidNode(mib, json_mib[key])
            except OidNodeInvalid:
                continue

            if not oid_node.is_object:
                continue

            if oid_node.is_middle_node:
                continue

            if oid_node.is_unknown_type:
                continue

            oid_list.append(oid_node)

    return oid_list


def _get_profiles_site_root():
    here = os.path.dirname(__file__)
    return os.path.abspath(
        os.path.join(here, '../../../../../../..', 'snmp', 'datadog_checks', 'snmp', 'data', 'profiles')
    )


def _resolve_profile_file(profile_file):
    if os.path.isabs(profile_file):
        return profile_file

    return os.path.join(_get_profiles_site_root(), profile_file)


def _load_profile_from_yaml(profile_filename):
    with open(_resolve_profile_file(profile_filename)) as f:
        return yaml.safe_load(f)


def _recursively_expand_profile(profile_filename, data):
    """
    Update `data` in-place with the contents of base profile files listed in the 'extends' section.

    Base profiles should be referenced by filename, which can be relative (built-in profile)
    or absolute (custom profile).

    Raises:
    * Exception: if any definition file referred in the 'extends' section was not found or is malformed.
    """

    expanded_data = _load_profile_from_yaml(profile_filename)
    expanded_metrics = expanded_data.get('metrics', [])
    existing_metrics = data.get('metrics', [])

    data['metrics'] = expanded_metrics + existing_metrics  # NOTE: expanded metrics must be added first.

    extends = expanded_data.get('extends', [])

    for base_filename in extends:
        _recursively_expand_profile(base_filename, data)


def _extract_oid_collection_from_profile_data(data):
    """
    Extract oids from profile `data`

    Return a collection of oid nodes, indexed by their oid
    """
    oid_collection = {}
    for metric in data['metrics']:
        oid_node = {'mib': metric['MIB']}
        if 'table' in metric:
            table = metric['table']
            if 'OID' in table:
                oid_node['name'] = table['name']
                oid_node['oid'] = table['OID']
                oid_collection[table['OID']] = oid_node
            if 'symbols' in table:
                for symbol in table['symbols']:
                    if 'OID' in symbol:
                        oid_node['name'] = symbol['name']
                        oid_node['oid'] = symbol['OID']
                        oid_collection[symbol['OID']] = oid_node
        elif 'symbol' in metric:
            symbol = metric['symbol']
            if 'OID' in symbol:
                oid_node['name'] = symbol['name']
                oid = symbol['OID']
                # remove trailing 0 from oid
                if oid.endswith('.0'):
                    oid = oid[:-2]
                oid_node['oid'] = oid
                oid_collection[oid] = oid_node
    return oid_collection


def _add_profile_table_node(profile_oid_collection, oid_node):
    """
    Updates a collection of profile nodes, indexed by oid, adding oid_node as a table node
    """
    if oid_node.node_type != 'table':
        raise ValueError('Must be a table node')

    mib = oid_node.mib
    name = oid_node.name
    oid = oid_node.oid

    profile_node = {'MIB': mib}
    table = {'name': name, 'OID': oid}
    if oid_node.description is not None:
        table['description'] = oid_node.description
    symbols = []
    metric_tags = []
    # find symbols for this table, they might be already added
    if oid in profile_oid_collection:
        symbols = profile_oid_collection[oid]['symbols']
        metric_tags = profile_oid_collection[oid]['metric_tags']

    profile_node['table'] = table
    profile_node['symbols'] = symbols
    profile_node['metric_tags'] = metric_tags
    profile_oid_collection[oid] = profile_node


def _load_aliases_from_yaml(aliases_path):
    # aliases:
    # - from:
    #     MIB: ENTITY-MIB
    #     name: entPhysicalIndex
    #   to:
    #     MIB: ENTITY-MIB
    #     name: entPhysicalName
    with open(aliases_path) as f:
        data = yaml.safe_load(f)

    if 'aliases' not in data:
        return None

    aliases = {}
    for item in data['aliases']:
        from_mib = item['from']['MIB']
        from_name = item['from']['name']
        aliases['{}:{}'.format(from_mib, from_name)] = item['to']

    return aliases


def _add_profile_row_node(
    profile_oid_collection,
    oid_node,
    mibs_directories,
    json_mib_directory,
    metric_tag_aliases_path,
    source,
    compiled_mibs_path,
):
    """
    Updates a collection of profile nodes, indexed by oid, adding indexes if found in oid_node
    """
    if oid_node.node_type != 'row':
        raise ValueError('Must be a row node')

    # return without any change when no index is available
    if oid_node.indices is None:
        return

    # load aliases
    aliases = None
    if metric_tag_aliases_path is not None:
        aliases = _load_aliases_from_yaml(metric_tag_aliases_path)

    # Row objects are table entry, often defining indexing for table rows
    # Table oids are defined as:
    # <TABLE_OID>.<TABLE_ENTRY>
    # where <TABLE_ENTRY> is always 1
    oid = oid_node.oid
    table_oid = '.'.join(oid.split('.')[:-1])
    if table_oid not in profile_oid_collection:
        # create table if it does not exist yet
        table = {'OID': table_oid}
        profile_node = {'table': table, 'symbols': [], 'metric_tags': []}
        profile_oid_collection[table_oid] = profile_node

    metric_tags = []
    for item in oid_node.indices:
        mib = item.index_module
        oid_name = item.index_name
        # look for an alias
        alias_key = '{}:{}'.format(mib, oid_name)
        if aliases is not None and alias_key in aliases:
            alias = aliases[alias_key]
            mib = alias['MIB']
            oid_name = alias['name']

        index = {'MIB': mib, 'tag': oid_name}
        column = {'name': oid_name}
        index_oid = _find_oid_by_name(mib, oid_name, mibs_directories, json_mib_directory, source, compiled_mibs_path)
        if index_oid is not None:
            column['OID'] = index_oid
            index_table_oid = '.'.join(index_oid.split('.')[:-2])
            index_table_name = _find_name_by_oid(
                mib, index_table_oid, mibs_directories, json_mib_directory, source, compiled_mibs_path
            )
            if index_table_name is not None:
                index['table'] = index_table_name
        index['column'] = column
        metric_tags.append(index)

    profile_oid_collection[table_oid]['metric_tags'] = metric_tags


def _add_profile_column_node(profile_oid_collection, oid_node):
    """
    Updates a collection of profile nodes, indexed by oid, adding a column node
    """
    if oid_node.node_type != 'column':
        raise ValueError('Must be a column node')
    name = oid_node.name
    # Table oids are defined as:
    # <TABLE_OID>.<TABLE_ENTRY>.<COLUMN_NUM>
    # where <TABLE_ENTRY> is always 1
    oid = oid_node.oid
    table_oid = '.'.join(oid.split('.')[:-2])
    if table_oid not in profile_oid_collection:
        # create table if it does not exist yet
        table = {'OID': table_oid}
        profile_node = {'table': table, 'symbols': [], 'metric_tags': []}
        profile_oid_collection[table_oid] = profile_node

    symbol = {'name': name, 'OID': oid}
    if oid_node.description is not None:
        symbol['description'] = oid_node.description
    symbols = profile_oid_collection[table_oid]['symbols']
    symbols.append(symbol)
    profile_oid_collection[table_oid]['symbols'] = symbols


def _add_profile_scalar_node(profile_oid_collection, oid_node):
    """
    Updates a collection of profile nodes, indexed by oid, adding a scalar node
    """
    if oid_node.node_type != 'scalar':
        raise ValueError('Must be a scalar node')
    name = oid_node.name
    mib = oid_node.mib
    oid = oid_node.oid

    profile_node = {'MIB': mib}
    if not oid.endswith('.0'):
        oid = oid + '.0'
    symbol = {'name': name, 'OID': oid}
    if oid_node.description is not None:
        symbol['description'] = oid_node.description
    profile_node['symbol'] = symbol
    profile_oid_collection[oid] = profile_node
