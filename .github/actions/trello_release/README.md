### Github Trello Action

This Github action is responsible for creating a Trello card in specific locations when Pull Requets are merged to the default branch for this repository.

The success or failure of the card creation is then emitted to Datadog as an Event.

The following environment variables are requuired for this Action to function:

* "TRELLO_LIST_ID" - The ID of the Trello list where cards should be created
* "DD_API_KEY" - To emit events to the Datadog account
* "TRELLO_TOKEN" - The trello token required to create the card
* "TRELLO_KEY" - Trello Users's API key, also required to create the card
