# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)
import requests


class TrelloClient:
    API_URL = 'https://api.trello.com'
    CREATE_ENDPOINT = API_URL + '/1/cards'

    def __init__(self, config):
        self.auth = {'key': config['trello']['key'] or None, 'token': config['trello']['token'] or None}
        self.team_list_map = {
            'Containers': '5ae1cab495edd80852396c71',
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
            'team/integrations': 'Integrations',
            'team/logs': 'Logs',
        }
        self.label_map = {
            'Containers': '5e7910856f8e4363e3b51708',
            'Core': '5e79105d4c45a45adb9e7730',
            'Integrations': '5e790ff25bd3dd48da67608d',
            'Logs': '5e79108febd27f4864c003ff',
            'Platform': '5e7910a45d711a6382f08bb9',
            'Networks': '5e79109821620a60014fc016',
            'Processes': '5e7910789f92a918152b700d',
            'Trace': '5c050640ecb34f0915ec589a',
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
