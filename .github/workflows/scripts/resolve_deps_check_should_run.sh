#!/bin/bash

if [ "$GITHUB_EVENT_NAME" == 'workflow_dispatch' ]; then
  builder_changed="false"
  should_run_build="true"
else

  cat << EOF > dependency_files.txt
agent_requirements\.in
\.github/workflows/resolve-build-deps\.yaml
\.builders/
EOF

  cat <<EOF > builder_files.txt
\.builders/
EOF

  should_run_build=$(
      echo "$FILES_CHANGED" | \
      grep -qf dependency_files.txt \
      && echo "true" || echo "false"
  )

  builder_changed=$(
      echo "$FILES_CHANGED" | \
      grep -qf builder_files.txt \
      && echo "true" || echo "false"
  )
fi

echo "should_run_build=$should_run_build" | tee -a $GITHUB_OUTPUT
echo "builder_changed=$builder_changed" | tee -a $GITHUB_OUTPUT
