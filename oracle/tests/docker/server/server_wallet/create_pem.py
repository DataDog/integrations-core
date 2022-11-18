# create_pem.py

import argparse
import getpass
import os

from cryptography.hazmat.primitives.serialization \
        import pkcs12, Encoding, PrivateFormat, BestAvailableEncryption, \
               NoEncryption

# parse command line
parser = argparse.ArgumentParser(description="convert PKCS#12 to PEM")
parser.add_argument("wallet_location",
                    help="the directory in which the PKCS#12 encoded "
                         "wallet file ewallet.p12 is found")
parser.add_argument("--wallet-password",
                    help="the password for the wallet which is used to "
                         "decrypt the PKCS#12 encoded wallet file; if not "
                         "specified, it will be requested securely")
parser.add_argument("--no-encrypt",
                    dest="encrypt", action="store_false", default=True,
                    help="do not encrypt the converted PEM file with the "
                         "wallet password")
args = parser.parse_args()

# validate arguments and acquire password if one was not specified
pkcs12_file_name = os.path.join(args.wallet_location, "ewallet.p12")
if not os.path.exists(pkcs12_file_name):
    msg = f"wallet location {args.wallet_location} does not contain " \
           "ewallet.p12"
    raise Exception(msg)
if args.wallet_password is None:
    args.wallet_password = getpass.getpass()

pem_file_name = os.path.join(args.wallet_location, "ewallet.pem")
pkcs12_data = open(pkcs12_file_name, "rb").read()
result = pkcs12.load_key_and_certificates(pkcs12_data,
                                          args.wallet_password.encode())
private_key, certificate, additional_certificates = result
if args.encrypt:
    encryptor = BestAvailableEncryption(args.wallet_password.encode())
else:
    encryptor = NoEncryption()
with open(pem_file_name, "wb") as f:
    f.write(private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8,
                                      encryptor))
    f.write(certificate.public_bytes(Encoding.PEM))
    for cert in additional_certificates:
        f.write(cert.public_bytes(Encoding.PEM))
print("PEM file", pem_file_name, "written.")