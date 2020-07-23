# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
from .config_block import ConfigBlock
from .utils import get_end_of_part, get_indent, is_at_least_indented, is_blank
from .validator_errors import SEVERITY_WARNING, ValidatorError


def validate_config(config):
    """Function used to validate a whole yaml configuration file. Will check if there are both the init_config and
    the instances sections. And will parse using the _parse_for_config_blocks function
    """
    errors = []
    blocks = []  # This will store ConfigBlocks as a tree
    config_lines = config.split('\n')

    init_config_line = -1
    instances_line = -1
    for i, line in enumerate(config_lines):
        if line.startswith("init_config:"):
            init_config_line = i
            if line != "init_config:":
                errors.append(ValidatorError("Expected no data after ':'", i, SEVERITY_WARNING))
        if line.startswith("instances:"):
            instances_line = i
            if line != "instances:":
                errors.append(ValidatorError("Expected no data after ':'", i, SEVERITY_WARNING))

    if init_config_line == -1:
        errors.append(ValidatorError("Missing `init_config` section", None))
        return errors

    if instances_line == -1:
        errors.append(ValidatorError("Missing `instances` section", None))
        return errors

    # parse init_config data
    blocks.append(_parse_init_config(config_lines, init_config_line, errors))

    # parse instances data
    instances_end = get_end_of_part(config_lines, instances_line)
    if instances_end is None:
        errors.append(ValidatorError("Malformed file, cannot find end of part 'instances'", instances_line))
        return errors
    blocks.append(_parse_for_config_blocks(config_lines, instances_line + 1, instances_end, errors))

    _check_no_duplicate_names(blocks, errors)
    _validate_blocks(blocks, errors)
    return errors


def _parse_init_config(config_lines, init_config_start_line, errors):
    """Function used to parse the init_config section and return the list of 'ConfigBlock'
    It first checks if the section contains data or not. If not, it returns an empty list. Otherwise
    it will use the _parse_for_config_blocks function to parse it between the beginning and the end of the part
    """
    blocks = []
    idx = init_config_start_line + 1

    # Check if the init_config part contains data or not
    while idx < len(config_lines):
        current_line = config_lines[idx]
        if is_blank(current_line):
            idx += 1
            continue
        elif is_at_least_indented(current_line, 1):
            # There is data in 'init_config'
            break
        else:
            # There is no data, do not try to parse the init_config
            return blocks

    end = get_end_of_part(config_lines, init_config_start_line)
    if end is None:
        errors.append(ValidatorError("Malformed file, cannot find end of part 'init_config'", init_config_start_line))
        return blocks

    return _parse_for_config_blocks(config_lines, init_config_start_line + 1, end, errors)


def _parse_for_config_blocks(config_lines, start, end, errors):
    """The function basically do all the work. It reads the config from start, removes blank lines first then when it first
    sees data, it sets the 'indent' variable once for all. All blocks read in a given function call must have the same
    indentation. Sub-blocks are parsed recursively and thus the 'indent' variable is given a new value.
    Once a block is parsed the function will either recurse if the block requires it (see ConfigBlock), or it will go
    to the next block and iterate.
    """
    idx = start
    blocks = []

    # Go to the first line with data (see 'is_blank')
    while idx < end:
        if is_blank(config_lines[idx]):
            idx += 1
            continue
        break
    else:
        return blocks

    # All blocks of a same level must have the same indentation. Let's use the first one to compare them
    indent = get_indent(config_lines[idx])

    while idx < end:
        current_line = config_lines[idx]
        if is_blank(current_line):
            idx += 1
            continue
        if not is_at_least_indented(current_line, indent):
            errors.append(ValidatorError("Content is not correctly indented - skipping rest of file", idx))
            # File will not be able to be parsed correctly if indentation is wrong
            return blocks

        cfg_block = ConfigBlock.parse_from_strings(idx, config_lines, indent, errors)
        # Even if there has been an issue when parsing the block, cfg_block.length always point to another block
        # (either a sub-block or not) or to EOF
        idx += cfg_block.length
        blocks.append(cfg_block)

        if cfg_block.should_recurse:
            # new_end points to the next line having the same indent as the cfg_block
            new_end = get_end_of_part(config_lines, idx, indent=indent)
            if new_end is None:
                block_name = cfg_block.param_prop.var_name if cfg_block.param_prop else "?"
                err_string = f"The object {block_name} cannot be parsed correctly, check indentation"
                errors.append(ValidatorError(err_string, idx))
                return blocks
            if new_end > end:
                new_end = end
            blocks += _parse_for_config_blocks(config_lines, idx, new_end, errors)
            idx = new_end

    return blocks


def _check_no_duplicate_names(blocks, errors):
    """blocks contains ConfigBlocks as a tree. This function makes sure that each yaml object has no duplicates
    variables and return a list of errors to be displayed if duplicates are found. The @param declaration needs to
    be there for this to correctly identify a variable.
    """
    same_level_blocks = [b for b in blocks if isinstance(b, ConfigBlock)]
    names_list = [b.param_prop.var_name for b in same_level_blocks if b.param_prop]
    duplicates = set([x for x in names_list if names_list.count(x) > 1])
    for dup in duplicates:
        errors.append(ValidatorError(f"Duplicate variable with name {dup}", None))

    sub_lists_of_other_blocks = [b for b in blocks if isinstance(b, list)]
    for l in sub_lists_of_other_blocks:
        _check_no_duplicate_names(l, errors)


def _validate_blocks(blocks, errors):
    """blocks contains ConfigBlocks as a tree. This function iterate over it to run the validate method on each
    ConfigBlock and append errors to the provided array if needed.
    """
    leaves = [b for b in blocks if isinstance(b, ConfigBlock)]
    for b in leaves:
        b.validate(errors)
    nodes = [b for b in blocks if isinstance(b, list)]
    for n in nodes:
        _validate_blocks(n, errors)
