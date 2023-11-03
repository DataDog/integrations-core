# Build dependencies for a specific system. Must be run from root of integrations-core.
set -exu

target_platform="${TARGET_PLATFORM}"
image_version="${AGENT_BUILD_IMAGE_VERSION:-latest}"

integrations_core_path="/integrations-core"
docker_image="datadog/agent-buildimages-${target_platform}:v20878799-a2f77ae"
build_script="/integrations-core/.deps-builder/build.sh"

# Docker login
if [ ! -z ${DOCKER_USERNAME:-} ];
then echo $DOCKER_ACCESS_TOKEN | docker login ${DOCKER_REGISTRY:-} -u $DOCKER_USERNAME --password-stdin
fi

# Run the omnibus build on the builder image
docker run \
       --mount type=bind,source="$(pwd)",target="${integrations_core_path}" \
       --name "agent-integrations-dependencies-builder" \
       "${docker_image}" \
       bash "${build_script}"
