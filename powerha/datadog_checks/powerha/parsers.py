# (C) Datadog, Inc. 2026-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
"""
Pure parsing functions for PowerHA/AIX command output.

Every function here takes a plain string (the stdout of one AIX or PowerHA
command) and returns plain Python data structures. None of them execute
anything or touch the filesystem, which is what makes them testable without
an AIX host: see tests/test_unit.py for fixture-driven coverage of every
parser below.

Unrecognized or malformed lines are skipped rather than raising, because
these command output formats are not all equally stable across AIX/PowerHA
versions (see tests/fixtures/README.md).
"""
import re

RG_KNOWN_STATES = frozenset(
    {
        'ONLINE',
        'OFFLINE',
        'ERROR',
        'UNMANAGED',
        'ACQUIRING',
        'RELEASING',
        'ONLINE_SECONDARY',
        'OFFLINE_SECONDARY',
        'ERROR_SECONDARY',
        'UNKNOWN',
    }
)


def parse_odm_stanzas(output):
    """
    Parse `odmget`-style ODM stanza output into a list of dicts.

    Stanza format (a stable, decades-old AIX interface):

        HACMPnode:
                name = "node1"
                node_id = 1

        HACMPnode:
                name = "node2"
                node_id = 2

    Returns one dict per stanza, e.g. [{'name': 'node1', 'node_id': '1'}, ...].
    Values are unquoted but not otherwise type-converted.
    """
    stanzas = []
    current = None
    attr_re = re.compile(r'^\s*(\w+)\s*=\s*(.*?)\s*$')

    for line in output.splitlines():
        if not line.strip():
            continue
        if not line[0].isspace():
            # A new stanza header, e.g. "HACMPnode:"
            current = {}
            stanzas.append(current)
            continue
        if current is None:
            continue
        match = attr_re.match(line)
        if not match:
            continue
        key, value = match.groups()
        current[key] = value.strip('"')

    return stanzas


def parse_lssrc_state(output):
    """
    Extract the `Current state: XXX` value from `lssrc -ls clstrmgrES` output.

    Returns the bare state token (e.g. 'ST_STABLE') or None if not found.
    """
    match = re.search(r'^\s*Current state:\s*(\S+)', output, re.MULTILINE)
    return match.group(1) if match else None


def parse_lslpp_version(output):
    """
    Extract the fileset version from `lslpp -Lc <fileset>` colon-delimited output.

    Format: fileset:fileset:VERSION:level:state:type:description:...
    """
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        fields = line.split(':')
        if len(fields) > 2 and fields[2]:
            return fields[2]
    return None


def find_last_event(text):
    """
    Scan `hacmp.out` text (or a tail of it) for the last "EVENT START" line
    and return the event name that follows it, or None.
    """
    event = None
    for line in text.splitlines():
        match = re.search(r'EVENT START:?\s*(\S+)', line)
        if match:
            event = match.group(1)
    return event


def parse_clrginfo_s(output):
    """
    Parse `clRGinfo -s` (or the legacy `clfindres -s`) colon-delimited output.

    Each row is at minimum `group:state:node`. A 9th field, if present and
    not itself a recognized resource-group state token, is treated as a
    site name (`rg_site`) -- see tests/fixtures/clrginfo_s_with_site.txt.

    Returns a list of dicts: {'group': ..., 'state': ..., 'node': ..., 'site': ... or None}.
    """
    rows = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        fields = line.split(':')
        if len(fields) < 3 or not fields[0] or not fields[1] or not fields[2]:
            continue

        site = None
        if len(fields) >= 9:
            candidate = fields[8].strip()
            if candidate and candidate.upper() not in RG_KNOWN_STATES:
                site = candidate

        rows.append({'group': fields[0], 'state': fields[1].upper(), 'node': fields[2], 'site': site})

    return rows


def parse_clrginfo_m(output):
    """
    Parse `clRGinfo -m` tabular application monitor output:

        -----------------------------------------------------------------
        Group Name     Application       Node             State
        -----------------------------------------------------------------
        appRG          appMonitor1       node1            ONLINE
        appRG          appMonitor1       node2            OFFLINE

    Returns a list of dicts: {'group': ..., 'application': ..., 'node': ..., 'state': ...}.
    """
    rows = []
    for line in output.splitlines():
        line = line.strip()
        if not line or set(line) == {'-'}:
            continue
        if line.startswith('Group Name'):
            continue

        fields = line.split()
        if len(fields) != 4:
            continue

        group, application, node, state = fields
        rows.append({'group': group, 'application': application, 'node': node, 'state': state.upper()})

    return rows


def parse_lscluster_m(output):
    """
    Parse `lscluster -m` free-text CAA node/interface topology output.

    Returns a list of dicts, one per node:
        {
            'node': str,
            'state': 'UP' | 'DOWN' | 'UNKNOWN',
            'points_of_contact': int,
            'interfaces': [{'name': str, 'state': 'UP' | 'DOWN'}, ...],
        }
    """
    nodes = []
    current = None
    in_poc_table = False

    node_re = re.compile(r'^Node name:\s*(\S+)')
    state_re = re.compile(r'^State of node:\s*(\S+)')
    poc_count_re = re.compile(r'Number of points_of_contact for node:\s*(\d+)')
    poc_header_re = re.compile(r'Point-of-contact interface')
    poc_row_re = re.compile(r'^(\S+)\s+(UP|DOWN)\s*$')

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        match = node_re.match(line)
        if match:
            current = {'node': match.group(1), 'state': 'UNKNOWN', 'points_of_contact': 0, 'interfaces': []}
            nodes.append(current)
            in_poc_table = False
            continue

        if current is None:
            continue

        match = state_re.match(line)
        if match:
            # e.g. "UP NODE_LOCAL" -> UP
            current['state'] = match.group(1).split()[0]
            in_poc_table = False
            continue

        match = poc_count_re.search(line)
        if match:
            current['points_of_contact'] = int(match.group(1))
            in_poc_table = False
            continue

        if poc_header_re.search(line):
            in_poc_table = True
            continue

        if in_poc_table:
            match = poc_row_re.match(line)
            if match:
                current['interfaces'].append({'name': match.group(1), 'state': match.group(2)})
                continue
            # Any other line ends the point-of-contact table for this node.
            in_poc_table = False

    return nodes


def parse_clras_status(output):
    """
    Parse `clras sancomm_status` / `clras dpcomm_status` pipe-delimited output.

    The header row is used to build a name -> column index map so the parser
    is immune to column reordering, e.g.:

        -----------------------------------
        NODE_NAME  |INTERFACE |UUID |STATUS
        -----------------------------------
        node1      |fscsi0    |...  |UP

    Returns a list of dicts keyed by the lowercased header names.
    """
    rows = []
    columns = None

    for line in output.splitlines():
        line = line.strip()
        if not line or set(line) == {'-'}:
            continue

        fields = [f.strip() for f in line.split('|')]
        if columns is None:
            if 'NODE_NAME' not in [f.upper() for f in fields]:
                continue
            columns = [f.lower() for f in fields]
            continue

        if len(fields) != len(columns):
            continue

        rows.append(dict(zip(columns, fields)))

    return rows


def parse_netstat_i(output):
    """
    Parse AIX `netstat -i` output into one row per interface.

    AIX emits two lines per interface (a `link#N` hardware row carrying the
    packet/error/collision counters, and one or more protocol rows); this
    collapses them into a single row per interface name, preferring the
    `link#` row for counters and any non-`link#` row for the IP address.
    A leading `*` on the interface name marks it administratively/physically
    down.
    """
    interfaces = {}
    order = []

    for line in output.splitlines():
        fields = line.split()
        if not fields or fields[0].lower() == 'name':
            continue
        if len(fields) < 8:
            continue

        raw_name = fields[0]
        down = raw_name.startswith('*')
        name = raw_name.lstrip('*')
        if name.startswith('lo'):
            continue

        network = fields[2]

        if name not in interfaces:
            interfaces[name] = {
                'name': name,
                'up': not down,
                'ip_address': None,
                'ipkts': None,
                'ierrs': None,
                'opkts': None,
                'oerrs': None,
                'collisions': None,
            }
            order.append(name)
        elif down:
            interfaces[name]['up'] = False

        if network.startswith('link#'):
            try:
                interfaces[name]['ipkts'] = int(fields[4])
                interfaces[name]['ierrs'] = int(fields[5])
                interfaces[name]['opkts'] = int(fields[6])
                interfaces[name]['oerrs'] = int(fields[7])
                if len(fields) > 8:
                    interfaces[name]['collisions'] = int(fields[8])
            except ValueError:
                continue
        else:
            interfaces[name]['ip_address'] = fields[3]

    return [interfaces[name] for name in order]


def parse_lsvg_o(output):
    """Parse `lsvg -o` output: one volume group name per line."""
    return [line.strip() for line in output.splitlines() if line.strip()]


def parse_lsvg_p(output):
    """
    Parse `lsvg -p <vg>` output:

        datavg:
        PV_NAME           PV STATE          TOTAL PPs   FREE PPs    FREE DISTRIBUTION
        hdisk2            active            511         200         102..00..00..98..00

    Returns a list of dicts: {'name', 'state', 'total_pps', 'free_pps'}.
    """
    rows = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.endswith(':') or line.upper().startswith('PV_NAME'):
            continue

        fields = line.split()
        if len(fields) < 4:
            continue

        name, state = fields[0], fields[1]
        try:
            total_pps = int(fields[2])
            free_pps = int(fields[3])
        except ValueError:
            continue

        rows.append({'name': name, 'state': state, 'total_pps': total_pps, 'free_pps': free_pps})

    return rows
