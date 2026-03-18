# This file is adapted from [sbdchd/codeowners] (https://github.com/sbdchd/codeowners),
# originally licensed under the MIT license. You can find the complete license text in the repository.

import re
from typing import Generator, List, Optional, Pattern, Tuple

from typing_extensions import Literal

OwnerTuple = Tuple[Literal["USERNAME", "TEAM", "EMAIL"], str]


TEAM = re.compile(r"^@\S+/\S+")
USERNAME = re.compile(r"^@\S+")
EMAIL = re.compile(r"^\S+@\S+")
MASK = "/" * 20


def path_to_regex(pattern: str) -> Pattern[str]:
    regex = ""

    slash_pos = pattern.find("/")
    anchored = slash_pos > -1 and slash_pos != len(pattern) - 1

    regex += r"\A/" if anchored else r"(?:\A|/)"

    matches_dir = pattern[-1] == "/"
    matches_no_subdirs = pattern[-2:] == "/*"
    pattern_trimmed = pattern.strip("/")

    in_char_class = False
    escaped = False

    iterator = enumerate(pattern_trimmed)
    for i, ch in iterator:
        if escaped:
            regex += re.escape(ch)
            escaped = False
            continue

        if ch == "\\":
            escaped = True
        elif ch == "*":
            if i + 1 < len(pattern_trimmed) and pattern_trimmed[i + 1] == "*":
                left_anchored = i == 0
                leading_slash = i > 0 and pattern_trimmed[i - 1] == "/"
                right_anchored = i + 2 == len(pattern_trimmed)
                trailing_slash = i + 2 < len(pattern_trimmed) and pattern_trimmed[i + 2] == "/"

                if (left_anchored or leading_slash) and (right_anchored or trailing_slash):
                    regex += ".*"

                    next(iterator, None)
                    next(iterator, None)
                    continue
            regex += "[^/]*"
        elif ch == "?":
            regex += "[^/]"
        elif ch == "[":
            in_char_class = True
            regex += ch
        elif ch == "]":
            if in_char_class:
                regex += ch
                in_char_class = False
            else:
                regex += re.escape(ch)
        else:
            regex += re.escape(ch)

    if in_char_class:
        raise ValueError(f"unterminated character class in pattern {pattern}")

    if matches_dir:
        regex += "/"
    elif matches_no_subdirs:
        regex += r"\Z"
    else:
        regex += r"(?:\Z|/)"
    return re.compile(regex)


def parse_owner(owner: str) -> Optional[OwnerTuple]:
    if TEAM.match(owner):
        return ("TEAM", owner)
    if USERNAME.match(owner):
        return ("USERNAME", owner)
    if EMAIL.match(owner):
        return ("EMAIL", owner)
    return None


class CodeOwners:
    def __init__(self, text: str) -> None:
        section_name = None

        paths: List[Tuple[Pattern[str], str, List[OwnerTuple], int, Optional[str]]] = []
        for line_num, line in enumerate(text.splitlines(), start=1):
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            # Track the GitLab section name (if used)
            # https://docs.gitlab.com/ee/user/project/code_owners.html#code-owners-sections
            elif line.startswith("[") and line.endswith("]"):
                section_name = line[1:-1]
                continue
            elif line.startswith("^[") and line.endswith("]"):
                section_name = line[2:-1]
                continue

            elements = iter(line.replace("\\ ", MASK).split())
            path = next(elements, None)
            if path is None:
                continue
            owners: List[OwnerTuple] = []
            for owner in elements:
                owner_res = parse_owner(owner)
                if owner_res is not None:
                    owners.append(owner_res)
            paths.append(
                (
                    path_to_regex(path),
                    path.replace(MASK, "\\ "),
                    owners,
                    line_num,
                    section_name,
                )
            )
        paths.reverse()
        self.paths = paths

    def matching_lines(
        self, filepath: str
    ) -> Generator[Tuple[List[OwnerTuple], Optional[int], Optional[str], Optional[str]], None, None]:
        for pattern, path, owners, line_num, section_name in self.paths:
            if pattern.search(filepath.replace(" ", MASK)) is not None:
                yield (owners, line_num, path, section_name)

    def matching_line(self, filepath: str) -> Tuple[List[OwnerTuple], Optional[int], Optional[str], Optional[str]]:
        return next(self.matching_lines(filepath), ([], None, None, None))

    def section_name(self, filepath: str) -> Optional[str]:
        """
        Find the section name of the specified file path.

        None is returned when no matching section information
        was found (or sections are not used in the CODEOWNERS file)
        """
        return self.matching_line(filepath)[3]

    def of(self, filepath: str) -> List[OwnerTuple]:
        return self.matching_line(filepath)[0]
