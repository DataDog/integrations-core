# (C) Datadog, Inc. 2018-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import click

from ....trello import TrelloClient
from ...console import CONTEXT_SETTINGS, echo_success
from .rc_build_cards_updater import RCBuildCardsUpdater


@click.command(context_settings=CONTEXT_SETTINGS, short_help='Update links to RCs in the QA board Trello cards')
@click.argument('target_ref')
@click.pass_context
def update_rc_links(ctx: click.Context, target_ref: str) -> None:
    user_config = ctx.obj
    trello = TrelloClient(user_config)
    rc_build_cards_updater = RCBuildCardsUpdater(trello, target_ref)
    rc_build_cards_updater.update_cards()
    echo_success('Done')
