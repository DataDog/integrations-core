FROM python:3.7

LABEL "com.github.actions.name"="Datadog Github-Trello"
LABEL "com.github.actions.description"="Create Trello card on merged PRs"
LABEL "com.github.actions.icon"="git-merge"
LABEL "com.github.actions.color"="blue"

LABEL "org.opencontainers.image.source"="https://github.com/DataDog/integrations-core"

COPY entrypoint.sh /entrypoint.sh
COPY requirements.in /requirements.in
COPY create_card.py /create_card.py

RUN pip install -rrequirements.in

ENTRYPOINT ["/entrypoint.sh"]
