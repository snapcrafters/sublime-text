#!/usr/bin/python3

import re
import urllib.request

URL_GET_LATEST = 'https://download.sublimetext.com/latest/stable'


def get_latest_version():
    with urllib.request.urlopen(URL_GET_LATEST) as response:
        return response.read().decode().strip()


def fetch_latest_version_details():
    version = get_latest_version()

    with open('snap/snapcraft.yaml') as f:
        lines = f.readlines()

    with open('snap/snapcraft.yaml', 'w') as f:
        for line in lines:
            if line.startswith('version:'):
                f.write(re.sub('version:.*', 'version: \'{}\''.format(version), line))
            else:
                f.write(line)


if __name__ == '__main__':
    fetch_latest_version_details()
