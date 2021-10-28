# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)


def get_end_of_part(config_lines, start_line, indent=None):
    """Returns the end of a yaml block for a given start line.

    If the indent parameter is unspecified, the start_line needs to be
    the start of a block. The indentation of that line will be used.
    You can specify the indent parameter to reach the end of the block
    with the provided indentation.

    :param config_lines: The yaml data as an array of strings
    :param start_line: Where to start looking for the end of a block
    :param indent: Optional, see description
    :return: The line at which the block ends.
             None if line is empty or if there is no block
    """
    i = start_line
    end = len(config_lines)
    if i >= end:
        return end

    if is_blank(config_lines[i]):
        return None

    if indent is None:
        indent = get_indent(config_lines[i])

    i += 1
    has_seen_data = False
    while i < end:
        if is_blank(config_lines[i]):
            i += 1
        elif is_at_least_indented(config_lines[i], indent + 1):
            i += 1
            has_seen_data = True
        else:
            end = i

    if not has_seen_data:
        return None

    return end


def get_indent(line):
    """Returns the indentation of a given line. According to YAML specs, indentation for list item does
    not start at the hyphen
    """
    if is_blank(line):
        return 0

    stripped = line.lstrip(' ')
    if stripped.startswith('- '):
        stripped = stripped[2:].lstrip(' ')
        # This is a list item

    return len(line) - len(stripped)


def is_blank(line):
    """Returns true if the line is empty.
    A single hyphen in a line is considered as blank
    """
    return line.isspace() or not line or line.strip() == '-'


def is_exactly_indented(line, indent):
    """Returns true if the line has the expected indentation. Empty line has no indentation"""
    if is_blank(line):
        return False
    return get_indent(line) == indent


def is_at_least_indented(line, indent):
    """Returns true if the line has at least the expected indentation. Empty line has no indentation"""
    if is_blank(line):
        return False
    return get_indent(line) >= indent
