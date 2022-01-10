# (C) Datadog, Inc. 2019-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import re

from .utils import get_indent, is_at_least_indented, is_blank, is_exactly_indented
from .validator_errors import SEVERITY_WARNING, ValidatorError

# The maximum length authorized for comments. It accounts for text after '##' and does not apply to the @param
# declaration
MAX_COMMENT_LENGTH = 120

# The list of accepted type as regex. Anything starting with list is allowed.
ACCEPTED_VAR_TYPE_REGEX = [
    "^boolean$",
    "^string$",
    "^integer$",
    "^double$",
    "^float$",
    "^object$",
    "^list.*$",
    "^dictionary$",
]

# Regex used to parse the fields of the '## @param' declaration
PARAM_REGEX = "^## @param ([a-zA-Z0-9_\\-]+) +- (.+) - (required|optional)( - default: .*)?$"

# Regex to parse a 'key: value' item
VAR_REGEX = "^(# |)(\\w+): ([a-zA-Z0-9_><]+)$"

# Regex to identify an object (it ends with a colon). No comment allowed after the colon but the whole line
# can be a comment.
OBJECT_REGEX = "^(# |)([a-zA-Z0-9_\\-]+): *$"

# Regex to identify a comment. Note that 'INDENT' needs to be updated with the number of spaces expected
COMMENT_REGEX = "^ {INDENT}##(.*)$"

# Regex to match any comment with no respect to indentation
INCORRECTLY_INDENTED_COMMENT_REGEX = "^ *##(.*)$"


class ParamProperties:
    """Class to represent a parameter declared using the '@param' annotation"""

    def __init__(self, var_name, type_name, required=True, default_value=None):
        self.var_name = var_name
        self.type_name = type_name
        self.required = required
        self.default_value = default_value

    @classmethod
    def parse_from_string(cls, idx, config_lines, indent, errors):
        if not is_exactly_indented(config_lines[idx], indent):
            errors.append(ValidatorError("Content is not correctly indented", idx))
            return None

        current_line = config_lines[idx][indent:]

        if not current_line.startswith("## @param"):
            errors.append(ValidatorError("Expecting @param declaration", idx))
            return None

        m = re.match(PARAM_REGEX, current_line)
        if m is None:
            errors.append(ValidatorError("Invalid @param declaration", idx))
            return None

        if m.group(3) == "optional":
            def_val = None
            if m.group(4):  # If there is a default value
                def_val = m.group(4)[12:]

            return cls(m.group(1), m.group(2), False, def_val)

        return cls(m.group(1), m.group(2), True)


class ConfigBlock:
    """Class to represent a 'configuration block' which is the definition of a variable, with the @param annotation,
    its description and its content.
    """

    def __init__(self, param_prop, description, line, length, should_recurse=False):
        """
        :param param_prop: ParamProperties instance
        :param description: The description preceding the variable declaration
        :param line: The first line of this block
        :param length: The number of lines this block takes. (see should_recurse)
        :param should_recurse: Whether or not the content of the block must be analyzed. See _should_recurse function
        """
        self.param_prop = param_prop
        self.description = description
        self.line = line
        self.length = length
        self.should_recurse = should_recurse

    def validate(self, errors):
        """Method to return a list of errors and warnings about an already parsed block"""
        self._validate_description(errors)
        self._validate_type(errors)

    def _validate_description(self, errors):
        """Check if the block has a description and lines are not too long."""
        if self.description is None:
            # There was a error reading description, which has already been recorded.
            return

        if self.description.strip() == '':
            param_name = self.param_prop.var_name
            errors.append(ValidatorError(f"Empty description for {param_name}", self.line, SEVERITY_WARNING))

        for i, line in enumerate(self.description.splitlines()):
            if len(line) > MAX_COMMENT_LENGTH and not line.endswith("#noqa"):
                err_string = f"Description too long [{line[:30]}...] ({len(line)}/{MAX_COMMENT_LENGTH})"
                errors.append(ValidatorError(err_string, self.line + i + 1))

    def _validate_type(self, errors):
        """Check if the block has a valid type"""
        if self.param_prop is None:
            return

        for regex in ACCEPTED_VAR_TYPE_REGEX:
            if re.match(regex, self.param_prop.type_name):
                break
        else:
            errors.append(ValidatorError(f"Type {self.param_prop.type_name} is not accepted", self.line))

    @classmethod
    def parse_from_strings(cls, start, config_lines, indent, errors):
        """Main method used to parse a block starting at line 'start' with a given indentation."""
        idx = start

        # Let's first check if the block is a simple comment. If so, let's return and go to the next block
        if _is_comment(start, config_lines, indent, errors):
            comment, end = _parse_comment(start, config_lines)
            return cls(None, comment, start, end - start)

        # Let's get to the end of the block supposing it is formatted correctly (@param line, description, empty
        # comment, then the actual content). If it fails, let's ignore the whole block and its potential
        # sub-blocks.
        end = _get_end_of_param_declaration_block(start, len(config_lines), config_lines, indent, errors)
        if end is None:
            default_end = _get_next_block_in_case_of_failure(start, config_lines)
            return cls(None, None, start, default_end - start)

        block_len = end - start

        # Parsing the @param line
        param_prop = ParamProperties.parse_from_string(idx, config_lines, indent, errors)
        if param_prop is None:
            return cls(None, None, start, block_len)

        # If var is indicated as list, recompute end of block knowing it is a list
        if param_prop.type_name.startswith('list'):
            end = _get_end_of_param_declaration_block(
                start, len(config_lines), config_lines, indent, errors, is_list=True
            )
            if end is None:
                default_end = _get_next_block_in_case_of_failure(start, config_lines)
                return cls(None, None, start, default_end - start)
            block_len = end - start

        # Parsing the description
        idx += 1
        description, idx = _parse_description(idx, end, config_lines, indent, errors)
        if idx is None:
            return cls(param_prop, None, start, block_len)

        # We recurse if the variable is an object and contains at least one member with description
        is_object = _is_object(idx, config_lines, indent, param_prop, errors)
        if not is_object:
            return cls(param_prop, description, start, block_len)

        should_recurse, next_block = _should_recurse(idx, config_lines, indent)
        if should_recurse:
            # If we recurse we use block_len, pointing to the next sub-block
            return cls(param_prop, description, start, block_len, should_recurse=True)

        # If we don't recurse we use the next_object variable to point to the next block with the same or less
        # indentation and thus ignore sub-blocks.
        block_len = next_block - start
        return cls(param_prop, description, start, block_len)


def _get_end_of_param_declaration_block(start, end, config_lines, indent, errors, is_list=False):
    """Here we suppose the config block is correctly formatted (@param, description, empty comment then the actual content)
    and try to return the line of any data coming after. In case of a object we point to its first member. In case
    of a list or a simple variable we point to the next element.
    """

    if not is_exactly_indented(config_lines[start], indent):
        other_indent = get_indent(config_lines[start])
        errors.append(ValidatorError(f"Unexpected indentation, expecting {indent} not {other_indent}", start))
        return None

    if not config_lines[start].startswith(' ' * indent + "## @param"):
        errors.append(ValidatorError("Expecting @param declaration", start))
        return None

    # Going through the description
    idx = start + 1
    while idx < end:
        if is_blank(config_lines[idx]):
            errors.append(ValidatorError("Blank line when reading description", idx))
            return None
        if not is_exactly_indented(config_lines[idx], indent):
            other_indent = get_indent(config_lines[idx])
            err_string = f"Unexpected indentation, expecting {indent} not {other_indent}"
            errors.append(ValidatorError(err_string, idx))
            return None

        current_line = config_lines[idx][indent:]
        if current_line[0:2] == '##':
            # This is still the description
            idx += 1
        elif current_line[0] == '#':
            # This is the last line of the description
            idx += 1
            break
        else:
            errors.append(ValidatorError(f"Cannot find end of block starting at line {start}", idx))
            return None

    # Now analyze the actual content
    idx += 1
    while idx < end:
        if is_blank(config_lines[idx]):
            idx += 1
            continue
        if not is_at_least_indented(config_lines[idx], indent):
            # We reached a surrounding block, thus this block has ended.
            break

        current_line = config_lines[idx][indent:]

        if current_line[0:2] == '# ':
            # Commented data
            idx += 1
        elif current_line.lstrip(' ').startswith('- '):
            # The object is a list of things, let's get to the end of that object
            is_list = True
            idx += 1
        elif is_list and is_at_least_indented(config_lines[idx], indent + 1):
            idx += 1
        else:
            break

    return idx


def _parse_description(idx, end, config_lines, indent, errors):
    """With idx pointing to the beginning of a description, it reads line by line and build the string. It returns
    the string and a pointer to the end of the description.
    """

    description = []
    while idx < end:
        if not is_exactly_indented(config_lines[idx], indent):
            if is_blank(config_lines[idx]):
                errors.append(ValidatorError("Reached end of description without marker", idx))
            else:
                errors.append(ValidatorError("Description is not correctly indented", idx))
            return None, None
        current_line = config_lines[idx][indent:]

        if current_line.startswith("##"):
            description.append(current_line[2:])
            idx += 1
        elif current_line[0] == '#' and is_blank(current_line[1:]):
            # End of description
            description = '\n'.join(description)
            idx += 1
            break
        else:
            description = '\n'.join(description)
            errors.append(ValidatorError("Reached end of description without marker", idx))
            return description, None
    else:
        # EOF reached without end of description
        errors.append(ValidatorError("Reached EOF while reading description", idx))
        return None, None

    return description, idx


def _is_object(idx, config_lines, indent, param_prop, errors):
    """With idx pointing to the beginning of a 'key: value' variable declaration, this function returns true
    if the variable is declared as an object in the @param declaration and if value is not on the same line.
    """

    if not is_exactly_indented(config_lines[idx], indent):
        errors.append(ValidatorError("Content is not correctly indented", idx))
        return False

    current_line = config_lines[idx][indent:]

    if param_prop.type_name == 'object':
        # The variable to be parsed is an object and thus requires to go recursively
        if re.match(OBJECT_REGEX, current_line) is None:
            err_string = f"Parameter {param_prop.var_name} is declared as object but isn't one"
            errors.append(ValidatorError(err_string, idx))
            return False
        return True

    return False


def _should_recurse(start, config_lines, initial_indent):
    """Sometimes object are not expected to document every parameter and contain all the description at the top.
    This is valid, therefore we should not recurse and analyze what's next after the whole object. Returns whether or
    not to recurse as long a pointer to the next same-level element (not sub-object)
    """
    idx = start + 1
    end = len(config_lines)

    # First get indent of the first member
    while idx < end:
        current_line = config_lines[idx]
        if is_blank(current_line) or current_line[initial_indent:].startswith('# '):
            idx += 1
            continue
        break
    else:
        # Reached EOF
        return False, idx

    current_line = config_lines[idx]
    first_member_indent = get_indent(current_line)

    if first_member_indent <= initial_indent:
        # We reached the end of object without any data
        return False, idx

    # Second check if there is description inside the object
    while idx < end:
        current_line = config_lines[idx]
        if is_blank(current_line):
            idx += 1
            continue
        if get_indent(current_line) <= initial_indent:
            # We reached end of object
            return False, idx
        if current_line.startswith(' ' * first_member_indent + "## @param"):
            # We found some description with the correct indentation. Let's recurse in that object
            return True, None
        idx += 1

    return False, idx


def _is_comment(start, config_lines, indent, errors):
    """Returns true if the block starting at line 'start' only contains comments and no @param declaration nor
    setting any variable.
    """

    regex = COMMENT_REGEX.replace('INDENT', str(indent))
    idx = start
    end = len(config_lines)
    if "## @param" in config_lines[idx]:
        # If we see @param, no matter how correctly formatted it is, we expect it to be a param declaration
        return False

    while idx < end:
        current_line = config_lines[idx]
        if re.match(regex, current_line):
            idx += 1
            continue
        elif is_blank(current_line):
            # End of block with only ## comments, the whole block is indeed only a comment
            return True
        elif re.match(INCORRECTLY_INDENTED_COMMENT_REGEX, current_line):
            # This is still a comment but incorrectly indented
            errors.append(ValidatorError("Comment block incorrectly indented", idx))
            idx += 1
            continue
        else:
            return False

    return True


def _parse_comment(start, config_lines):
    """If we are reading a multiline comment, let's read it and find the index of the next block to be parsed.
    Return a tuple of the comment and the index of the next block"""
    idx = start
    end = len(config_lines)
    comment = []
    # Get to end of multiline comment
    while idx < end:
        current_line = config_lines[idx]
        if re.match(INCORRECTLY_INDENTED_COMMENT_REGEX, current_line):
            content = current_line.lstrip(' ')[2:]
            comment.append(content)
            idx += 1
            continue
        break

    comment = '\n'.join(comment)
    # Get to next data
    while idx < end:
        current_line = config_lines[idx]
        if is_blank(current_line):
            idx += 1
            continue
        break
    return comment, idx


def _get_next_block_in_case_of_failure(start, config_lines):
    """If we can't read a param declaration correctly, let's default to this method to continue parsing
    from the next block"""
    idx = start
    end = len(config_lines)
    initial_indent = get_indent(config_lines[idx])

    # First get rid of blank lines and comments
    while idx < end:
        current_line = config_lines[idx]
        if is_blank(current_line) or current_line.lstrip(' ').startswith('#'):
            idx += 1
            continue
        break

    # Now wait for the first same-level comment to get back on track
    while idx < end:
        current_line = config_lines[idx]
        if is_exactly_indented(current_line, initial_indent) and current_line[initial_indent] == '#':
            break
        idx += 1

    return idx
