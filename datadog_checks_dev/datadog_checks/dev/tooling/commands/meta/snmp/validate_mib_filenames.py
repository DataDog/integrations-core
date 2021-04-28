# (C) Datadog, Inc. 2021-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import os
import re
from collections import namedtuple

import click
from tabulate import tabulate

from ...console import CONTEXT_SETTINGS, echo_info, echo_warning

OPTION_ALL = '*'

OPTION_HELP = '''Use a supported option to select all files, one single file, a range of files or multiple ranges
Option supports:
> * all
> 1 single index
> 1-4 range of indexes from 1 to 4 excluded
> 1-4:6 multiple ranges
Example:
1-3:6-9
selects files 1,2 and 6,7,8
2
selects file 2
1:3:5-9
selects files 1,3,5,6,7,8
1:4
selects files 1,2,3
'''

# (
#   (
#     \d+     # one or more digits
#     (-\d+)* # zero or one character'-' followed by one or more digits
#   ){1} # exactly once
#   (
#     :\d+    # one character ':' followed by one or more digits
#     (-\d+)* # zero or one character'-' followed by one or more digits
#   )*  # one or more
# )
# |  # OR
# \* # one character '*'
OPTION_PATTERN = r'((\d+(-\d+)*){1}(:\d+(-\d+)*)*)|\*'

MibFile = namedtuple('MibFile', ['index', 'folder', 'base_filename', 'name', 'is_valid'])


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Validate MIB file names')
@click.argument('mib_files', nargs=-1)
@click.option('--interactive', '-i', is_flag=True, help='Prompt to confirm before renaming all invalid MIB files')
@click.pass_context
def validate_mib_filenames(ctx, mib_files, interactive):
    """
    Validate MIB file names. Frameworks used to load mib files expect MIB file names to match
    MIB name.
    """
    # filter files
    mib_files = [f for f in mib_files if os.path.isfile(f)]
    # ensure at least one mib file is provided
    if len(mib_files) == 0:
        echo_warning('🙄 no mib file provided, need at least one mib file to validate them')
        return

    mibs = []
    # build profile
    index = 1
    for mib_file in mib_files:
        if not os.path.isfile(mib_file):
            continue
        mib_name = _load_and_extract_mib_name(mib_file)

        base_filename = os.path.basename(mib_file)
        mibs.append(
            MibFile(
                index,
                folder=os.path.dirname(os.path.realpath(mib_file)),
                base_filename=base_filename,
                name=mib_name,
                is_valid=mib_name and mib_name == base_filename.split('.')[0],
            )
        )
        index += 1

    option = '*'
    if interactive:
        echo_info(
            tabulate(
                [[mib.index, mib.base_filename, mib.name, mib.is_valid] for mib in mibs],
                headers=['Index', 'File', 'Name', "Valid"],
            )
        )
        option = click.prompt(
            text='🤖 Which files do you want to rename? (* for all, 1 for single, 1-3:5-7 for range(s))',
            default=OPTION_ALL,
        )

    _rename_mib_files([mib for mib in mibs if not mib.is_valid], option)


def _load_and_extract_mib_name(mib_file):
    with open(mib_file) as f:
        read_data = f.read()
        return _extract_mib_name(read_data)
    return None


def _extract_mib_name(mib_data):
    for line in mib_data.splitlines():
        if 'DEFINITIONS ::= BEGIN' in line:
            name = line.split('DEFINITIONS ::=')[0].strip()
            return name
    return None


def _rename_mib_files(mibs, option='*'):
    if not _is_valid_option(option):
        echo_warning('⚠️ Invalid option')
        echo_info(OPTION_HELP)
        return

    # filter indexes
    if option != OPTION_ALL:
        indexes = set()
        # parse ranges
        for opt_range in option.split(':'):
            if '-' in opt_range:
                # parse index ranges
                # ie: 1-7
                start, end = opt_range.split('-')
                indexes.update(range(int(start), int(end)))
            else:
                # parse single index
                # ie: 1
                indexes.add(int(opt_range))
        mibs = [mib for mib in mibs if mib.index in indexes]

    # rename
    for mib in mibs:
        dst = mib.name
        if '.' in mib.base_filename:
            extension = mib.base_filename.split('.')[1]
            dst += '.{}'.format(extension)
        os.rename(src=os.path.join(mib.folder, mib.base_filename), dst=os.path.join(mib.folder, dst))


def _is_valid_option(option):
    return re.fullmatch(OPTION_PATTERN, option)
