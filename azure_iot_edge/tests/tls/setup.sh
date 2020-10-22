#! /bin/bash -e

# Automated script for steps described in:
# Adapted from: https://docs.microsoft.com/en-us/azure/iot-edge/how-to-create-test-certificates

DIR="azure_iot_edge/tests/tls"

cd $DIR

TEST_DEVICE_NAME='testEdgeDevice'
CA_CERT_NAME='mighty-candy'  # Something unrelated to the device name.

# Create root CA certificate.
./certGen.sh create_root_and_intermediate
echo 'SUCCESS: created root CA certificate:'
echo

# Verify root CA certificate so that test device can communicate with IoT Hub.
echo "Please upload $DIR/certs/azure-iot-test-only.root.ca.cert.pem to IoT Hub to generate downstream device certificate, then generate a verification code."
echo 'See: https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-security-x509-get-started#register-x509-ca-certificates-to-your-iot-hub'
echo 'Enter verification code:'
read VERIFICATION_CODE
./certGen.sh create_verification_certificate $VERIFICATION_CODE
./certGen.sh create_device_certificate $TEST_DEVICE_NAME
echo
echo 'SUCCESS: created device certificate files'
echo
echo "Please upload $DIR/certs/verification-code.cert.pem to IoT Hub to complete certificate validation"
echo "See steps 7/ and 8/ here: https://docs.microsoft.com/en-us/azure/iot-hub/iot-hub-security-x509-get-started#register-x509-ca-certificates-to-your-iot-hub"
echo "Once done, certificate should show as 'Verified' in IoT Hub web UI."
