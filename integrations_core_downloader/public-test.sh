#!/bin/bash

set -e -x

SIMPLE_INDEX=https://dd-integrations-core-wheels-build-stable.s3.amazonaws.com/targets/simple/index.html
VENV=integrations-core-downloader-venv

clear
python3 -m venv $VENV
source $VENV/bin/activate

pip3 install --upgrade .

rm -f *.tar.gz
rm -f *.whl
rm -f *.zip

# https://stackoverflow.com/a/21264899
curl -s $SIMPLE_INDEX | sed -n "s/.*href='\(datadog-[^/\']*\).*/\1/p" | while read -r PACKAGE; do
  # -v:     CRITICAL
  # -vv:    ERROR
  # -vvv:   WARNING
  # -vvvv:  INFO
  # -vvvvv: DEBUG
  integrations-core-downloader $PACKAGE -vvvv
  echo
done

rm -f *.tar.gz
rm -f *.whl
rm -f *.zip

deactivate
