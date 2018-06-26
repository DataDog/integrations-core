#!/usr/bin/env zsh


pushd ../datadog_checks_base
  pip wheel -e . --no-deps
  scp datadog_checks_base-1.2.2-py2-none-any.whl cisco-box:~/wheels
  rm -f datadog_checks_base-1.2.2-py2-none-any.whl
popd

pip wheel -e . --no-deps
scp datadog_cisco_aci-1.0.0-py2-none-any.whl cisco-box:~/wheels
rm -f datadog_cisco_aci-1.0.0-py2-none-any.whl

# scp ./datadog_checks/cisco_aci/cisco.py cisco-box:~/cisco.py

scp installer.sh cisco-box:~/
scp just_install_cisco.sh cisco-box:~/just_install_cisco.sh

ssh cisco-box "./just_install_cisco.sh"
ssh cisco-box "./just_restart.sh"

pushd ..
  inv cleanup
popd
