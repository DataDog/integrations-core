workflow "Create Trello Card" {
  resolves = ["Datadog Github-Trello"]
  on = "pull_request"
}

action "Datadog Github-Trello" {
  uses = "./.github/actions/trello_release"
  secrets = ["DD_API_KEY", "TRELLO_KEY", "TRELLO_LIST_ID", "TRELLO_TOKEN"]
}
