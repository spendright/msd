# -*- coding: utf-8 -*-

#   Copyright 2014-2015 SpendRight, Inc.
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""Harness for running msd on morph.io. Downloads source databases
and merges them into data.sqlite.

To run this, you'll need a free morph.io account. Set MORPH_API_KEY
to the value of your key.
"""
from logging import getLogger
from os import environ
from urllib.parse import urlencode
from urllib.request import urlopen

from msd.cmd import run
from msd.cmd import set_up_logging


SCRAPER_DATA = {
    'sr.company': 'https://morph.io/spendright/scrape-companies/data.sqlite',
    'sr.campaign': 'https://morph.io/spendright/scrape-campaigns/data.sqlite',
    'sr.url': 'https://morph.io/spendright/scrape-urls/data.sqlite',
}

CHUNK_SIZE = 1024  # for download()

OUTPUT_PATH = 'data.sqlite'

log = getLogger('scraper')


def main():
    if 'MORPH_API_KEY' not in environ:
        raise ValueError(
            'Must set MORPH_API_KEY to download scraper data'.format(db_name))

    set_up_logging(quiet=environ.get('MORPH_QUIET'),
                   verbose=environ.get('MORPH_VERBOSE'))


    input_paths = []

    for scraper_id, url in sorted(SCRAPER_DATA.items()):
        full_url = '{}?{}'.format(
            url, urlencode(dict(key=environ['MORPH_API_KEY'])))
        path = scraper_id + '.sqlite'

        # don't show API key in output
        log.info('downloading {} -> {}'.format(url, path))
        download(full_url, path)
        input_paths.append(path)

    run(force_rebuild_scratch=True,
        input_db_paths=input_paths,
        output_db_path=OUTPUT_PATH)



def download(url, path):
    with open(path, 'wb') as f:
        with urlopen(url) as src:
            while True:
                chunk = src.read(CHUNK_SIZE)
                if not chunk:
                    break
                f.write(chunk)


if __name__ == '__main__':
    main()
