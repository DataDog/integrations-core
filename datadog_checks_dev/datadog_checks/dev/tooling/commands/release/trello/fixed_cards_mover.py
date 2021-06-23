# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import re
from typing import Dict, List, Tuple

from ....trello import TrelloClient
from ...console import echo_success


class FixedCardsMover:
    GITHUB_TRELLO_ACTION_ID = '56097d35feef6f3281d58087'
    GITHUB_URL_REGEX = 'https://github.com/DataDog/datadog-agent/pull/\\d*'

    def __init__(self, client: TrelloClient, dry_run: bool):
        self.__client = client
        self.__ids_by_url: Dict[str, List[str]] = {}
        self.__ids_by_url_from_comment: Dict[str, List[str]] = {}
        self.__dry_run = dry_run

        for column in [
            client.FIXED_READY_TO_REBUILD_COLUMN,
            client.HAVE_BUG_FIXE_ME_COLUMN,
        ]:
            list_json = client.get_list(column)
            for l in list_json:
                card_id = l['id']
                urls = self.__get_github_pull_requests_urls(card_id)
                self.__append_dict(self.__ids_by_url, urls, card_id)

                urls = self.__get_github_pull_requests_urls_from_comments(card_id)
                self.__append_dict(self.__ids_by_url_from_comment, urls, card_id)

    def __append_dict(self, dict: Dict[str, List[str]], keys: List[str], value: str):
        for key in keys:
            if key not in dict:
                dict[key] = []
            dict[key].append(value)

    def try_move_card(self, github_url: str) -> bool:
        card_ids = self.__get_matching_card_ids(github_url)
        return len(card_ids) == 1 and self.__try_move_card(card_ids[0], github_url)

    def __get_matching_card_ids(self, github_url: str) -> List[str]:
        if github_url in self.__ids_by_url:
            return self.__ids_by_url[github_url]
        if github_url in self.__ids_by_url_from_comment:
            return self.__ids_by_url_from_comment[github_url]
        return []

    def __try_move_card(self, card_id: str, github_url: str) -> bool:
        card = self.__client.get_card(card_id)
        url = card['url']
        id_labels = card['idLabels']
        team_name, id_list = self.__get_team_info(id_labels)
        if id_list == '':
            return False

        if self.__dry_run:
            echo_success(f'Will move the card {url} to the INBOX column of team {team_name}')
        else:
            echo_success(f'Moving the card {url} to the INBOX column of team {team_name}')
            self.__client.move_card(card_id, id_list)
            self.__client.add_comment(card_id, f'Test the Github pull request {github_url}')
        return True

    def __get_team_info(self, id_labels: List[str]) -> Tuple[str, str]:
        # Card should have a single label but ignore the card if it is not the case
        if len(id_labels) != 1:
            return '', ''
        team_name = self.__client.get_team_name_from_id_label(id_labels[0])
        if team_name:
            id_list = self.__client.get_id_list_from_team_name(team_name)
            return team_name, id_list
        return '', ''

    def __get_github_pull_requests_urls(self, card_id: str) -> List[str]:
        urls = set([])
        attachements = self.__client.get_attachments(card_id)
        for attachement in attachements:
            if 'idMember' in attachement and attachement['idMember'] == self.GITHUB_TRELLO_ACTION_ID:
                urls.add(attachement['url'])
        return list(urls)

    def __get_github_pull_requests_urls_from_comments(self, card_id: str) -> List[str]:
        urls = set([])
        actions = self.__client.get_actions(card_id)
        for action in actions:
            if action['type'] == 'commentCard':
                data = action['data']
                text = data['text']
                github_urls = re.findall(self.GITHUB_URL_REGEX, text)
                for u in github_urls:
                    urls.add(u)
        return list(urls)
