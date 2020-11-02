# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import requests


class TrelloClient:
    API_URL = 'https://api.trello.com'
    CREATE_ENDPOINT = API_URL + '/1/cards'
    BOARD_ENDPOINT = API_URL + '/1/boards/ICjijxr4/cards'
    LISTS_ENDPOINT = API_URL + '/1/boards/ICjijxr4/lists'
    LABELS_ENDPOINT = API_URL + '/1/boards/ICjijxr4/labels'
    CARDS_ENDPOINT = API_URL + '/1/cards'
    MEMBERSHIP_ENDPOINT = API_URL + '/1/boards/ICjijxr4/memberships'
    MEMBER_ENPOINT = API_URL + '/1/members'
    HAVE_BUG_FIXE_ME_COLUMN = '58f0c271cbf2d534bd626916'
    FIXED_READY_TO_REBUILD_COLUMN = '5d5a8a50ca7a0189ae8ac5ac'

    def __init__(self, config):
        self.auth = {'key': config['trello']['key'] or None, 'token': config['trello']['token'] or None}
        self.team_list_map = {
            'Containers': '5ae1cab495edd80852396c71',
            'Container App': '5e8b36a8060eeb1cb3fa5a9c',
            'Core': '5ae1e3d62a5167779e65e87d',
            'Integrations': '5ae1e3e2c81fff836d00497e',
            'Logs': '5aeca4c19707c4222bf6d883',
            'Platform': '5d9b687492952e6578ecf04d',
            'Networks': '5e1de8cf867357791ec5ee47',
            'Processes': '5aeca4c8621e4359b9cb9c27',
            'Trace': '5bcf3ffbe0651642ae029038',
            'Tools and Libraries': '5ef373fb33b7b805120d5011',
            'Runtime-Security': '5f3148683b7428276f0f2133',
            'Infra Integrations': '5f9f9e09af18c18c628d80ee',
        }
        self.label_team_map = {
            'team/agent-apm': 'Trace',
            'team/agent-core': 'Core',
            'team/agent-platform': 'Platform',
            'team/networks': 'Networks',
            'team/processes': 'Processes',
            'team/containers': 'Containers',
            'team/container-app': 'Container App',
            'team/integrations': 'Integrations',
            'team/logs': 'Logs',
            'team/intg-tools-libs': 'Tools and Libraries',
            'team/agent-security': 'Runtime-Security',
            'team/infra-integrations': 'Infra Integrations',
        }

        self.label_github_team_map = {
            'team/agent-apm': 'agent-apm',
            'team/agent-core': 'agent-core',
            'team/agent-platform': 'agent-platform',
            'team/networks': 'networks',
            'team/processes': 'processes',
            'team/containers': 'container-integrations',
            'team/container-app': 'container-app',
            'team/integrations': 'agent-integrations',
            'team/logs': 'logs-intake',
            'team/intg-tools-libs': 'integrations-tools-and-libraries',
            'team/agent-security': 'agent-security',
            'team/infra-integrations': 'infrastructure-integrations',
        }

        self.label_map = {
            'Containers': '5e7910856f8e4363e3b51708',
            'Container App': '5e8b36f72f642272e75edd34',
            'Core': '5e79105d4c45a45adb9e7730',
            'Integrations': '5e790ff25bd3dd48da67608d',
            'Logs': '5e79108febd27f4864c003ff',
            'Platform': '5e7910a45d711a6382f08bb9',
            'Networks': '5e79109821620a60014fc016',
            'Processes': '5e7910789f92a918152b700d',
            'Trace': '5c050640ecb34f0915ec589a',
            'Tools and Libraries': '5ab12740841642c2a8829053',
            'Runtime-Security': '5f314f0a364ee16ea4e78868',
            'Infra Integrations': '5f9fa48537fb6633584b0e3e',
        }
        self.progress_columns = {
            '55d1fe4cd3192ab85fa0f7ea': 'In Progress',  # INPROGRESS
            self.HAVE_BUG_FIXE_ME_COLUMN: 'Issues Found',  # HAVE BUGS
            self.FIXED_READY_TO_REBUILD_COLUMN: 'Awaiting Build',  # WAITING
            '5dfb4eef503607473af708ab': 'Done',
        }

        self.__check_map_consistency(self.team_list_map, self.label_team_map, self.label_map)

    def __check_map_consistency(self, team_list_map, label_team_map, label_map):
        if len(team_list_map) != len(label_team_map):
            raise Exception('`team_list_map` and `label_team_map` do not have the same size')
        if len(team_list_map) != len(label_map):
            raise Exception('`team_list_map` and `label_map` do not have the same size')
        if team_list_map.keys() != label_map.keys():
            raise Exception(
                f'Keys should be the same for `team_list_map` and `label_map` {team_list_map.keys()} '
                + 'vs {label_map.keys()}'
            )
        for team in label_team_map.values():
            if team not in team_list_map:
                raise Exception(f'Team {team} cannot be found in `team_list_map`')

    def create_card(self, team, name, body, member=None):
        rate_limited = False
        error = None
        response = None

        params = {
            'idList': self.team_list_map[team],
            'idLabels': self.label_map[team],
            'name': name,
            # It appears the character limit for descriptions is ~5000
            'desc': body[:5000],
        }

        params.update(self.auth)

        if member:
            params['idMembers'] = [member]

        try:
            response = requests.post(self.CREATE_ENDPOINT, params=params)
        except Exception as e:
            error = str(e)
        else:
            try:
                response.raise_for_status()
            except Exception as e:
                error = str(e)

        # Rate limit
        if response:
            rate_limited = response.status_code == 429

        return rate_limited, error, response

    def count_by_columns(self):
        """
        Gather statistics for each category in the Trello board.

        """
        map_label = {v: k for k, v in self.label_map.items()}
        map_team_list = {v: k for k, v in self.team_list_map.items()}

        counts = {
            k: {'Total': 0, 'Inbox': 0, 'In Progress': 0, 'Issues Found': 0, 'Awaiting Build': 0, 'Done': 0}
            for k in map_label.values()
        }

        cards = requests.get(self.BOARD_ENDPOINT, params=self.auth)
        for card in cards.json():
            labels = card.get('labels', [])
            for label in labels:
                if label['name'] in self.label_map:
                    team = label['name']
                    id_list = card['idList']

                    if id_list in map_team_list:
                        counts[team]['Total'] += 1
                        counts[team]['Inbox'] += 1
                    elif id_list in self.progress_columns:
                        counts[team]['Total'] += 1
                        counts[team][self.progress_columns[id_list]] += 1

        return counts

    def get_card(self, card_id):
        response = requests.get(f'{self.CARDS_ENDPOINT}/{card_id}', params=self.auth)
        response.raise_for_status()
        return response.json()

    def update_card(self, card_id, data):
        headers = {'Content-Type': 'application/json'}
        response = requests.put(f'{self.CARDS_ENDPOINT}/{card_id}', headers=headers, data=data, params=self.auth)
        response.raise_for_status()
        return response.json()

    def get_membership(self):
        """
        Get the members.
        """
        membership = requests.get(self.MEMBERSHIP_ENDPOINT, params=self.auth)
        membership.raise_for_status()
        return membership.json()

    def get_member(self, id_member):
        """
        Get the member.
        """
        try:
            membership = requests.get(f'{self.MEMBER_ENPOINT}/{id_member}', params=self.auth)
            membership.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                raise Exception('Timeout, please try in 900 secondes') from e
            else:
                raise e

        return membership.json()

    def get_list(self, list_id):
        return self.__request(self.API_URL + f'/1/lists/{list_id}/cards')

    def get_attachments(self, card_id):
        return self.__request(self.API_URL + f'/1/cards/{card_id}/attachments')

    def get_actions(self, card_id):
        return self.__request(self.API_URL + f'/1/cards/{card_id}/actions')

    def move_card(self, card_id, id_list):
        return self.__request(self.API_URL + f'/1/cards/{card_id}?idList={id_list}', requests.put)

    def add_comment(self, card_id, comment):
        return self.__request(self.API_URL + f'/1/cards/{card_id}/actions/comments?text={comment}', requests.post)

    def __request(self, url, action=requests.get):
        response = action(url, params=self.auth)
        response.raise_for_status()
        return response.json()

    def get_team_name_from_id_label(self, id_label):
        for team_name, current_id_label in self.label_map.items():
            if current_id_label == id_label:
                return team_name
        return None

    def get_id_list_from_team_name(self, team_name):
        return self.team_list_map[team_name]
