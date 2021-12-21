import os
import urllib.request
import zipfile

TARGET_PATH = "/tmp/67f55o00o0oo" #"c:\\ibm_mq"
VERSION = "9.2.2.0"
ZIP_FILE = "{}-IBM-MQC-Redist-Win64.zip".format(VERSION)
IBM_URL = "https://public.dhe.ibm.com/ibmdl/export/pub/software/websphere/messaging/mqdev/redist/{}".format(ZIP_FILE)

try:
    os.mkdir(TARGET_PATH)
    print("Successfully created the directory %s " % TARGET_PATH)
except OSError:
    print("Creation of the directory %s failed" % TARGET_PATH)
    raise


print("Downloading IBM MQ client")
zip_path, _ = urllib.request.urlretrieve(IBM_URL, os.path.join(TARGET_PATH, ZIP_FILE))

print("Extracting IBM MQ client")
with zipfile.ZipFile(zip_path, "r") as f:
    f.extractall(TARGET_PATH)

print(os.listdir(TARGET_PATH))
