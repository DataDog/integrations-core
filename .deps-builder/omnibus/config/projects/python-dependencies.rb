# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https:#www.datadoghq.com/).
# Copyright 2023-present Datadog, Inc.
require "./lib/ostools.rb"

name 'python-dependencies'

homepage 'http://www.datadoghq.com'
maintainer 'Datadog, Inc <package@datadoghq.com>'

dependency 'datadog-agent-integrations-dependencies-py3'

INSTALL_DIR = '/opt/datadog-agent'

install_dir INSTALL_DIR
build_version ENV['PACKAGE_VERSION']

package :zipper do
  target "frozen.txt"
  target "wheels"
end
