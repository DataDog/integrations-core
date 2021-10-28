# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from .....github import Github
from .....trello import TrelloClient
from ....console import echo_info, echo_warning
from .github_trello_user_matcher import GithubTrelloUserMatcher
from .github_users import GithubUser, GithubUsers, pr_date_str_to_date
from .tester_selector_team import TesterSelectorTeam
from .trello_users import TrelloUser, TrelloUsers


def create_tester_selector(trello: TrelloClient, repo: str, github_teams: List[str], user_config, app_dir: str):
    github = Github(user_config, 5, repo, 'DataDog')
    now = datetime.utcnow()
    user_cache_expiration = now + timedelta(days=-7)
    trello_users = TrelloUsers(trello, app_dir, user_cache_expiration)
    github_users = GithubUsers(github, app_dir, user_cache_expiration)
    userMatcher = GithubTrelloUserMatcher(trello_users)

    inactivity_date = now + timedelta(days=-(6 * 7))  # Duration of the release
    return TesterSelector(github_teams, github_users, userMatcher, github, inactivity_date)


class TesterSelector:
    """
    Select a teammmate for QAing a trello card from github author.
    The algorithm is described in TesterSelectorTeam.
    Only users who created a pull request after `inactivity_date` are
    considered.
    """

    def __init__(
        self,
        team_names: List[str],
        github_users: GithubUsers,
        matcher: GithubTrelloUserMatcher,
        github: Github,
        inactivity_date: datetime,
    ):

        self.__teams: Dict[str, TesterSelectorTeam] = {}
        self.__trello_user_from_github_login: Dict[str, TrelloUser] = {}

        for user in github_users.get_users(team_names):
            last_activity_date = self.__get_last_user_activity(user)
            login = user.login
            if last_activity_date and last_activity_date > inactivity_date:
                self.__add_user(user, matcher, github)
            else:
                echo_info(f'Skip inactive user {login} {last_activity_date}')

    def get_next_tester(self, author: str, team_name: str, pr_num: int) -> Optional[TrelloUser]:
        if team_name not in self.__teams:
            return None
        team = self.__teams[team_name]
        github_login = team.get_next_tester(author, pr_num)

        if github_login in self.__trello_user_from_github_login:
            return self.__trello_user_from_github_login[github_login]
        return None

    def get_stats(self):
        stats = {}
        for team in self.__teams.values():
            stats[team.get_name()] = team.get_stats()
        return stats

    def __add_user(self, github_user: GithubUser, matcher: GithubTrelloUserMatcher, github: Github):
        team = self.__get_or_create_team(github_user, github)
        login = github_user.login
        team.add(login)

        trello_user = matcher.get_trello_user(login, github_user.name)
        if not trello_user:
            echo_warning(f'No trello user found for {login}')
        else:
            self.__trello_user_from_github_login[login] = trello_user

    def __get_or_create_team(self, github_user: GithubUser, github: Github):
        team_name = github_user.team
        if team_name not in self.__teams:
            self.__teams[team_name] = TesterSelectorTeam(github, team_name)
        return self.__teams[team_name]

    def __get_last_user_activity(self, user: GithubUser) -> Optional[datetime]:
        last_pr_date = user.last_pr_date_str
        if last_pr_date:
            return pr_date_str_to_date(last_pr_date)
        return None
