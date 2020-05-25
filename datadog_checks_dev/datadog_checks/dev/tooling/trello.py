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
        }
        self.progress_columns = {
            '55d1fe4cd3192ab85fa0f7ea': 'In Progress',  # INPROGRESS
            '58f0c271cbf2d534bd626916': 'Issues Found',  # HAVE BUGS
            '5d5a8a50ca7a0189ae8ac5ac': 'Awaiting Build',  # WAITING
            '5dfb4eef503607473af708ab': 'Done',
        }

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
            k: {'Total': 0, 'In Progress': 0, 'Issues Found': 0, 'Awaiting Build': 0, 'Done': 0}
            for k in map_label.values()
        }

        cards = requests.get(self.BOARD_ENDPOINT, params=self.auth)
        for card in cards.json():
            labels = card.get('labels', [])
            for label in labels:
                if label['name'] in self.label_map:
                    team = label['name']
                    counts[team]['Total'] += 1
                    id_list = card['idList']
                    if id_list in map_team_list:
                        # Team's Inbox
                        # NOTE: This is "In Progress" but not technically started, yet
                        counts[team]['In Progress'] += 1
                    elif id_list in self.progress_columns:
                        counts[team][self.progress_columns[id_list]] += 1

        return counts
