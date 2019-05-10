workflow "Create Trello Card" {
  on = "pull_request"
  resolves = ["Datadog Github-Trello"]
}

action "Datadog Github-Trello" {
  uses = "./.github/actions/trello_release"
  secrets = ["DD_API_KEY", "TRELLO_KEY", "TRELLO_LIST_ID", "TRELLO_TOKEN"]
}
