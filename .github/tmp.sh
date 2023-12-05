REQUESTED_TEAMS=$(jq -r '.event.pull_request.requested_teams[].name' < tmp.json)

for team in $(jq -r '.event.pull_request.requested_teams[].name' < tmp.json); do
  # if team is not in REQUIRED_TEAMS, print the name of the team

done