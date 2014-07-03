import codecs
import logging
import sqlite3
from os import environ
from os import rename
from os.path import exists
from tempfile import NamedTemporaryFile
from urllib import urlencode
from urllib2 import urlopen
from sys import stdout

CHUNK_SIZE = 1024


log = logging.getLogger('scraper')

DB_TO_URL = {
    'campaigns': 'https://morph.io/spendright-scrapers/campaigns/data.sqlite',
}

# various misspellings of company names
COMPANY_CORRECTIONS = {
    'V.F. Corporation': 'VF Corporation',
    'Wolverine Worldwide': 'Wolverine World Wide',
}


def merge_sets(elt_to_set, elts):
    """Update elt_to_set so that all elements in elts point to the
    same set, by merging sets."""
    if not elts:
        return

    elts = sorted(elts)

    for e in elts:
        if e not in elt_to_set:
            elt_to_set[e] = set([e])

    dest = elt_to_set[elts[0]]

    # merge other sets into dest
    for e in elts[1:]:
        if elt_to_set[e] is not dest:
            dest.update(elt_to_set[e])
            elt_to_set[e] = dest







def main():
    logging.basicConfig(format='%(name)s: %(message)s', level=logging.INFO)

    out = codecs.getwriter('utf8')(stdout)
    for company in get_companies():
        out.write(company + '\n')


def get_companies():
    campaigns_db = open_db('campaigns')

    return sorted(row[0] for row in campaigns_db.execute(
        'SELECT company from campaign_company'))


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

        open_db._name_to_db[name] = sqlite3.connect(filename)

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


if __name__ == '__main__':
    main()
