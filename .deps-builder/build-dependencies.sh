# Build dependencies for a specific system. Must be run from root of integrations-core.
set -ex

target_platform="$1"
image_version="v20878799-a2f77ae"
docker_image="486234852809.dkr.ecr.us-east-1.amazonaws.com/ci/datadog-agent-buildimages/${target_platform}:${image_version}"
build_script="/integrations-core/.deps-builder/build.sh"
# This is only necessary for running amd64 linux images on M1 as part of experimenting locally
platform_flag="--platform=linux/amd64"

docker run \
       --mount type=bind,source="$(pwd)",target=/integrations-core \
       --name "agent-integrations-dependencies-builder" \
       ${platform_flag} \
       "${docker_image}" \
       bash -c "${build_script}"
