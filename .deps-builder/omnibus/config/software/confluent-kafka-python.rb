# https://github.com/confluentinc/confluent-kafka-python/blob/master/INSTALL.md#install-from-source

name "confluent-kafka-python"
default_version "2.2.0"

dependency "agent-requirements-constraints"

source :url => "https://github.com/confluentinc/confluent-kafka-python/archive/refs/tags/v#{version}.tar.gz",
       :sha256 => "ee099702bd5fccd3ce4916658fed4c7ef28cb22e111defb843d27633100ff065",
       :extract => :seven_zip

relative_path "confluent-kafka-python-#{version}"

build do
  license "Apache-2.0"
  license_file "./LICENSE.txt"

  if windows?
    python_build_env.wheel "confluent-kafka"
  else
    dependency "librdkafka"

    build_env = {
      "CFLAGS" => "-I#{install_dir}/embedded/include -std=c99"
    }
    python_build_env.wheel "--no-binary confluent-kafka .", env: build_env
  end
end
