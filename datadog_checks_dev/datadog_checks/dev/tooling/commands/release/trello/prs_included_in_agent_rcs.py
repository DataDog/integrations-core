# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

from typing import Callable, Dict, List, Tuple

from ...console import echo_info
from .tester_selector.github_users import GithubUsers

prs_included_in_agent_rcs_link = (
    'https://docs.google.com/spreadsheets/d/1rwI6_8MYEDTcC92uNuPRZC565QUVuNtMSYZyc4uLEdQ/edit#gid=1406957277'
)


class PRsIncludedInAgentRc:
    def __init__(self, github_users: GithubUsers, base_ref: str):
        self.__team_by_user: Dict[str, str] = {}
        for user in github_users.get_users():
            self.__team_by_user[user.login] = user.team
        self.__base_ref = base_ref
        self.__author_url_collection: List[Tuple[str, str]] = []

    def add(self, pr_author: str, pr_url: str):
        self.__author_url_collection.append((pr_author, pr_url))

    def dump_prs_list(self, filename):
        self.__dump_to_file(
            filename, None, lambda author, url, team: f'=SPLIT("{url}, {team}, {self.__base_ref}", ",")'
        )
        echo_info(
            f'\nThe list of PRs for `PRs included in Agent RCs`: {prs_included_in_agent_rcs_link}'
            + f' are written to `{filename}`.'
        )

    def dump_slack_message(self, filename: str):
        title = f'Please update "PRs included in Agent RCs": {prs_included_in_agent_rcs_link}\n'
        self.__dump_to_file(filename, title, lambda author, url, team: f' - {url}: {author} ({team})')
        echo_info(f'\nThe Slack message for `PRs included in Agent RCs` is written to `{filename}`')

    def __dump_to_file(self, filename: str, title: str, callback: Callable[[str, str, str], str]):
        with open(filename, 'w') as f:
            if title:
                f.write(f'{title}\n')
            for author, url in self.__author_url_collection:
                if author not in self.__team_by_user:
                    team = "Unknown"
                else:
                    team = self.__team_by_user[author]
                line = callback(author, url, team)
                f.write(f'{line}\n')
