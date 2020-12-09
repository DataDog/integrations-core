# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import json
import re

from ....trello import TrelloClient
from ...console import abort, echo_info


class RCBuildCardsUpdater:
    version_regex = r'(\d*)\.(\d*)\.(\d*)([-~])rc([\.-])(\d*)'

    def __init__(self, trello: TrelloClient, release_version: str):
        self.__trello = trello
        match = re.fullmatch(self.version_regex, release_version)
        if not match:
            abort(
                f'Cannot update cards in RC builds columnn. '
                f'`{release_version}` is an invalid release candidate version. '
                f'A valid version is for example `7.21.0-rc.3`. '
                f'You can disable the update of cards in RC builds column by removing --update-rc-builds-cards'
            )
        else:
            groups = match.groups()
            if len(groups) != 6:
                raise Exception('Regex in RCBuildCardsUpdater is not correct')

            (_, self.__minor, self.__patch, _, _, self.__rc) = groups

    def update_cards(self):
        rc_build_cards = [
            'Rrn1Y0yU',  # [A7] Windows + Docker + Chocolatey
            'DyjjKkZD',  # [A6] Windows
            'BOvSs9Le',  # [IOT] Linux
            'hu1JXJ18',  # [A7] Linux + Docker
            'E7bHwa14',  # [A6] Linux + Docker
            'dYrSpOLW',  # MacOS
        ]

        for card_id in rc_build_cards:
            card = self.__trello.get_card(card_id)
            description = card['desc']
            new_version = f'\\g<1>.{self.__minor}.{self.__patch}\\g<4>rc\\g<5>{self.__rc}'
            new_description = re.sub(self.version_regex, new_version, description)
            updated_card = {'desc': new_description}
            echo_info(f'updating release version for the card {card["name"]}')
            self.__trello.update_card(card_id, json.dumps(updated_card))
