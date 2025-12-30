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

  cat << EOF > direct_deps_files.txt
agent_requirements\.in
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

  direct_deps_changed=$(
      echo "$FILES_CHANGED" | \
      grep -qf direct_deps_files.txt \
      && echo "true" || echo "false"
  )

  # If agent_requirements.in changed but the commit already contains an updated `.deps/metadata.json`
  # matching its SHA, we can skip rebuilding/uploading/resolving again (avoids the "second PR" case).
  if [ "$builder_changed" == "false" ] && [ "$direct_deps_changed" == "true" ]; then
    deps_already_resolved="$(python -c "import hashlib,json; from pathlib import Path; direct=Path('agent_requirements.in'); metadata=Path('.deps/metadata.json'); \
ok=direct.is_file() and metadata.is_file(); \
expected=hashlib.sha256(direct.read_bytes()).hexdigest() if ok else ''; \
data=json.loads(metadata.read_text(encoding='utf-8')) if ok else {}; \
print('true' if (ok and data.get('sha256') == expected) else 'false')")"
    if [ "$deps_already_resolved" == "true" ]; then
      should_run_build="false"
    fi
  fi
fi

echo "should_run_build=$should_run_build" | tee -a $GITHUB_OUTPUT
echo "builder_changed=$builder_changed" | tee -a $GITHUB_OUTPUT
