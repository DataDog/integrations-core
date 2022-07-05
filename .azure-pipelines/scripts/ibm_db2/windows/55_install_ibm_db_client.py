import os
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import requests

CLIENT_ARCHIVE_NAME = 'ntx64_odbc_cli.zip'
CLIENT_URL = f'https://ddintegrations.blob.core.windows.net/ibm-db2/{CLIENT_ARCHIVE_NAME}'
CLIENT_TARGET_DIR = 'C:\\ibm_db2'


def download_file(url, file_name):
    response = requests.get(url, stream=True)
    response.raise_for_status()

    with open(file_name, 'wb') as f:
        for chunk in response.iter_content(16384):
            f.write(chunk)


def main():
    with TemporaryDirectory() as d:
        temp_dir = os.path.realpath(d)

        print('Downloading client')
        client_archive_path = os.path.join(temp_dir, CLIENT_ARCHIVE_NAME)
        download_file(CLIENT_URL, client_archive_path)

        print('Extracting client')
        with ZipFile(client_archive_path) as zip_file:
            zip_file.extractall(CLIENT_TARGET_DIR)


if __name__ == '__main__':
    main()
