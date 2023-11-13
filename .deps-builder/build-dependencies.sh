# Build dependencies for a specific system. Must be run from root of integrations-core.
set -exu

target_platform="${TARGET_PLATFORM}"
image_version="${AGENT_BUILD_IMAGE_VERSION:-latest}"

docker_image="datadog/agent-buildimages-${target_platform}:${image_version}"

if [ -z "${RUNNING_ON_WINDOWS:-}" ];
then
    mount_target="/integrations-core"
    mount_source="$(pwd)"
    build_command="bash ${mount_target}/.deps-builder/build.sh"
else
    mount_target='c:\integrations-core'
    mount_source="$(cmd //c cd)"
    build_command='c:\integrations-core\.deps-builder\buildwin.bat'
fi

# Docker login
if [ ! -z ${DOCKER_USERNAME:-} ];
then echo $DOCKER_ACCESS_TOKEN | docker login ${DOCKER_REGISTRY:-} -u $DOCKER_USERNAME --password-stdin
fi

# Run the omnibus build on the builder image
docker run \
       --mount type=bind,source="${mount_source}",target="${mount_target}" \
       --name "agent-integrations-dependencies-builder" \
       "${docker_image}" \
       ${build_command}

