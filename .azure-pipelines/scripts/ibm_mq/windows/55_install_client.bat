#:: https://docs.microsoft.com/en-us/sql/connect/odbc/windows/system-requirements-installation-and-driver-files
#:: Finding the actual URL not gated by a form was a nightmare
# This script installs IBM MQ development version on the CI machines to be able to
# * Compile pymqi image
# * Run integration tests on the machine

RUN Powershell -C .\install_ibm_mq.ps1 "9.2.2.0"
