# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import string
import unicodedata
from typing import Dict, Optional

from .trello_users import TrelloUser, TrelloUsers


class GithubTrelloUserMatcher:
    """
    Find the Trello user from a Github user using heuristics

    See `__normalize_github_name` for Github name normalization and
    `__normalize_trello_name` for Trello name normalization
    """

    def __init__(self, trello_users: TrelloUsers):
        users = trello_users.get_users()
        self.__normalized_trello_users: Dict[str, TrelloUser] = {}
        for user in users:
            self.__add_trello_user(user.full_name, user)
            self.__add_trello_user(user.username, user)

    def get_trello_user(self, github_login: str, github_username: str) -> Optional[TrelloUser]:
        names = [github_login]
        if github_username:
            names.append(github_username)
        for name in names:
            normalized_name = self.__normalize_github_name(name)
            if normalized_name in self.__normalized_trello_users:
                return self.__normalized_trello_users[normalized_name]
        return None

    def __normalize_github_name(self, name: str) -> str:
        """
        Remove spaces and `-dd` suffix, replace accents and convert the result to lower case.
        """
        name = name.replace(" ", "")
        name = self.__strip_accents(name).lower()
        suffix = "-dd"
        if name.endswith(suffix):
            name = name[: -len(suffix)]
        return name

    def __strip_accents(self, text: str):
        text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode("utf-8")
        return str(text)

    def __normalize_trello_name(self, name: str):
        """
        Remove space, `@datadoghq.com`, `.`, postfix digits and convert the result to lower case
        """
        name = name.replace(" ", "").replace("@datadoghq.com", "").replace(".", "")
        name = name.lower().rstrip(string.digits)
        return name

    def __add_trello_user(self, name: str, user: TrelloUser):
        normalize_name = self.__normalize_trello_name(name)
        if normalize_name not in self.__normalized_trello_users:
            self.__normalized_trello_users[normalize_name] = user
        else:
            existing_user = self.__normalized_trello_users[normalize_name]
            if existing_user != user:
                raise Exception(f'Normalized name is the same for {existing_user} and {user}')
