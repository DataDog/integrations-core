# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import time
from datetime import datetime
from typing import Dict, List, Optional, cast

from .....github import Github
from ....console import echo_info
from .cache import Cache


class GithubUser:
    def __init__(self, data: Dict[str, object]):
        self.login = cast(str, data['login'])
        self.name = cast(str, data['name'])
        self.last_pr_date_str = ''
        last_pr_date_str = data['last_pr_date_str']
        if last_pr_date_str:
            self.last_pr_date_str = cast(str, last_pr_date_str)
        self.team = cast(str, data['team'])


class GithubUsers:
    """
    Store a collection of Github users
    """

    def __init__(self, github: Github, app_dir: str, cache_expiration: datetime):
        self.__github = github
        # Use a cache to avoid API Rate Limits
        self.__user_cache = Cache(app_dir, 'github_user', cache_expiration)

    def get_users(self, teams: List[str]) -> List[GithubUser]:
        github_users = cast(Dict[str, Dict[str, object]], self.__user_cache.get_value())
        if not github_users:
            github_users = {}
        for team in teams:
            echo_info(f'Get team members for {team}')
            for member in self.__github.get_team_members(team):
                login = member['login']
                if login not in github_users:
                    user = self.__github.get_user(login)
                    date = self.get_last_pr_date(login)
                    github_users[login] = {'login': login, 'name': user['name'], 'last_pr_date_str': date, 'team': team}
                    time.sleep(1)  # to avoid timeout

        self.__user_cache.set_value(github_users)
        return [GithubUser(user) for user in github_users.values()]

    def get_last_pr_date(self, login: str) -> Optional[str]:
        last_prs = self.__github.get_last_prs(login)
        last_prs_items = last_prs['items']
        if len(last_prs_items) == 0:
            return None
        last_pr = last_prs_items[0]
        created_at = last_pr['created_at']
        return created_at
