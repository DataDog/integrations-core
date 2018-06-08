#!/bin/bash
#
# This script makes sure that Gitlab is up and running, before trying to
# register the Runner
#
# At the end of these steps, a Runner with metrics enabled is expected to be up
set -euo pipefail

echo "Waiting for Gitlab to be up..."

while true
do
	# Allow this command to fail
	set +e
	curl -SsLf http://gitlab 2>&1 > /dev/null
	retval=$?
	set -e

	if [ $retval -eq 0 ]; then
		echo "Gitlab is up!"
		break
	fi
	sleep 5
done

# Register the runner and start the Prometheus metrics server
set +x
gitlab-ci-multi-runner register -u http://gitlab -r $GITLAB_SHARED_RUNNERS_REGISTRATION_TOKEN --executor shell -n
gitlab-runner run --user=gitlab-runner --working-directory=/home/gitlab-runner --metrics-server 0.0.0.0:9292
set -x

