# -*- coding: utf-8 -*-

#   Copyright 2014 David Marin
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
"""Download and open databases."""

import logging
import sqlite3
from os import environ
from os import rename
from os.path import exists
from tempfile import NamedTemporaryFile
from urllib import urlencode
from urllib2 import urlopen


DB_TO_URL = {
    'campaigns': 'https://morph.io/spendright-scrapers/campaigns/data.sqlite',
}

CHUNK_SIZE = 1024

OUT_DB_TMP_FILENAME = 'data.tmp.sqlite'
OUT_DB_FILENAME = 'data.sqlite'


log = logging.getLogger(__name__)


def open_db(name):
    if not hasattr(open_db, '_name_to_db'):
        open_db._name_to_db = {}

    if name not in open_db._name_to_db:
        filename = name + '.sqlite'
        if not exists(filename):
            if 'MORPH_API_KEY' not in environ:
                raise ValueError(
                    'Must set MORPH_API_KEY to download {} db'.format(name))

            url = DB_TO_URL[name] + '?' + urlencode(
                {'key': environ['MORPH_API_KEY']})

            log.info('downloading {} -> {}'.format(url, filename))
            download(url, filename)
        else:
            log.info('opening local copy of {}'.format(filename))

        db = sqlite3.connect(filename)
        db.row_factory = sqlite3.Row
        open_db._name_to_db[name] = db

    return open_db._name_to_db[name]


def download(url, dest):
    with NamedTemporaryFile(prefix=dest + '.tmp.', dir='.', delete=False) as f:
        src = urlopen(url)
        while True:
            chunk = src.read(CHUNK_SIZE)
            if not chunk:
                break
            f.write(chunk)

        f.close()
        rename(f.name, dest)


def out_db():
    """Open a DB for output in a temp file"""
    if not hasattr(out_db, '_db'):
        out_db._db = sqlite3.connect(OUT_DB_TMP_FILENAME)

    return out_db._db


def close_out_db():
    """Move out_db into place."""
    out_db._db.close()
    del out_db._db

    rename(OUT_DB_TMP_FILENAME, OUT_DB_FILENAME)
