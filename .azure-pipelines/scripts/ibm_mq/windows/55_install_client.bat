#:: This script installs IBM MQ development version on the CI machines to be able to
#:: * Compile pymqi image
#:: * Run integration tests on the machine

dir .azure-pipelines\scripts\ibm_mq\windows
powershell -Command .azure-pipelines\scripts\ibm_mq\windows\install_ibm_mq.ps1 "9.2.2.0"
