# (C) Datadog, Inc. 2020-present
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import random
from typing import Dict, List, Optional, Set

from .....github import Github


class TesterSelectorTeam:
    """
    Select a teammmate for QAing a trello card from a github PR author.

    The algorithm is the following:
        1 Consider teammates who are neither the author of the PR nor a reviewer.
        2 Select the teammate with the least number of assigned cards. If several
          teammates meet these criterion, select one randomly.

        If a tester cannot be find, use 2 but consider teammates that review the PR.

        Note: If someone review all the PRs of her team, the algorithm never select her.
    """

    def __init__(self, github: Github, team_name: str):
        self.__prs_by_tester: Dict[str, List[int]] = {}
        self.__name = team_name
        self.__github = github

    def add(self, user: str):
        self.__prs_by_tester[user] = []

    def get_next_tester(self, author: str, pr_num: int) -> Optional[str]:
        exclude_testers = self.__get_reviewers(pr_num)
        exclude_testers.add(author)

        # find a tester who is neither the author nor a reviewer
        tester = self.__select_testers(lambda t: t in exclude_testers)
        if tester is None:
            # find a tester who is not the author
            tester = self.__select_testers(lambda t: t != author)

        if tester is not None:
            self.__prs_by_tester[tester].append(pr_num)
        return tester

    def get_stats(self):
        return self.__prs_by_tester

    def get_name(self):
        return self.__name

    def __select_testers(self, user_excluded_fct) -> Optional[str]:
        candidates: List[str] = []
        minAssignedCards = 0
        for user, prs in self.__prs_by_tester.items():
            if not user_excluded_fct(user):
                if len(candidates) == 0 or len(prs) <= minAssignedCards:
                    # if a user has less reviews than minAssignedCards, then
                    # she becomes the current best candidate.
                    if len(prs) < minAssignedCards:
                        candidates.clear()
                    candidates.append(user)
                    minAssignedCards = len(prs)

        if len(candidates) > 0:
            return candidates[random.randint(0, len(candidates) - 1)]
        return None

    def __get_reviewers(self, pr_num: int) -> Set[str]:
        reviews = self.__github.get_reviews(pr_num)
        return set([r["user"]["login"] for r in reviews])
