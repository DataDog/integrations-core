import os
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import requests


CLIENT_VERSION = '9.2.5.0'
CLIENT_ARCHIVE_NAME = f'{CLIENT_VERSION}-IBM-MQC-Redist-Win64.zip'
CLIENT_URL = f'https://ddintegrations.blob.core.windows.net/ibm-mq/{CLIENT_ARCHIVE_NAME}'
CLIENT_TARGET_DIR = 'C:\\ibm_mq'


def download_file(url, file_name):
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(file_name, 'wb') as f:
        for chunk in response.iter_content(16384):
            f.write(chunk)


def main():
    with TemporaryDirectory() as d:
        temp_dir = os.path.realpath(d)

        print('Downloading client from %s' % CLIENT_URL)
        client_archive_path = os.path.join(temp_dir, CLIENT_ARCHIVE_NAME)
        download_file(CLIENT_URL, client_archive_path)

        print('Extracting client to %s ' % CLIENT_TARGET_DIR)
        with ZipFile(client_archive_path) as zip_file:
            zip_file.extractall(CLIENT_TARGET_DIR)


if __name__ == '__main__':
    main()
