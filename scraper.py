import codecs
import logging
import sqlite3
import re
from os import environ
from os import rename
from os.path import exists
from tempfile import NamedTemporaryFile
from unidecode import unidecode
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

COMPANY_ALIASES = [
    ['AB Electrolux', 'Electrolux'],
    ['Disney', 'The Walt Disney Company', 'The Walt Disney Co.'],
    ['HP', 'Hewlett-Packard'],
    ['LG', 'LG Electronics', 'LGE'],
]

# X & Co. -- okay to strip
X_AND_CO_RE = re.compile(
    r'^(?P<company>.*) \& Co\.?$'
)

# "The X Company" -- okay for matching, but don't use as short name
THE_X_COMPANY_RE = re.compile(
    r'^The (?P<company>.*) (Co\.|Corporation|Cooperative|Company|Group)$')

# "X Company" -- okay for matching, but don't use as short name
X_COMPANY_RE = re.compile(
    r'^(?P<company>.*) ('
    r'Co.'
    r'|Company'
    r'|Corporation'
    r'|Enterprises'
    r'|Group'
    r'|Gruppe'
    r')$'
)



COMPANY_TYPE_RE = re.compile(
    r'^(?P<company>.*?),? (?P<type>'
    r'A\.?& S\. Klein GmbH \& Co\. KG'
    r'|A/S'
    r'|AB'
    r'|AG'
    r'|AS'
    r'|Ab'
    r'|B\.V\.'
    r'|C\.V\.'
    r'|Corp.'
    r'|GmbH \& C[oO]\. [oO]HG'
    r'|GmbH \& Co\. ?KG\.?'  # handle typo: Lukas Meindl GmbH & Co.KG
    r'|GmbH \& Co\. KGaA'
    r'|GmbH'
    r'|Inc\.?'
    r'|KG\.?'
    r'|LLC'
    r'|LLP'
    r'|LP'
    r'|Limited'
    r'|Llp'
    r'|Ltd\.?'
    r'|Ltda\.?'
    r'|NV'
    r'|N\.V\.'
    r'|PBC'  # "Public Benefit Corporation"? Only on B Corp site
    r'|PLC'
    r'|P\.C\.'
    r'|P\.C\.'
    r'|Pty Ltd'
    r'|Pty'
    r'|S.\L\.'
    r'|SA'
    r'|SAPI DE CV SOFOM ENR'
    r'|SARL'
    r'|SE'
    r'|S\.A\.'
    r'|S\.A\.U\.'
    r'|S\.R\.L\.'
    r'|S\.p\.A\.'
    r'|b\.v\.'
    r'|gmbh'
    r'|inc'
    r'|plc'
    r')$'
)

COMPANY_TYPE_CORRECTIONS = {
    'Llp': 'LLP',
    'NV': 'N.V.',
    'b.v.': 'B.V.',
    'gmbh': 'GmbH',
    'inc': 'Inc',
}


# use this to turn e.g. "babyGap" into "baby Gap"
# this can also turn "G.I. Joe" into "G. I. Joe"
CAMEL_CASE_RE = re.compile('(?<=[a-z\.])(?=[A-Z])')

# use to remove excess whitespace
WHITESPACE_RE = re.compile(r'\s+')





def main():
    logging.basicConfig(format='%(name)s: %(message)s', level=logging.INFO)

    out = codecs.getwriter('utf8')(stdout)
    for company in get_companies():
        display_variants, matching_variants = company_name_variants(company)
        out.write(u'{}: {} {}\n'.format(
            company, repr(sorted(display_variants)),
            repr(sorted(matching_variants))))


def simplify_whitespace(s):
    """Strip s, and use only single spaces within s."""
    return WHITESPACE_RE.sub(' ', s.strip())


def norm(s):
    return unidecode(s).lower()


def norm_with_variants(s):
    variants = set()

    variants.add(norm(CAMEL_CASE_RE.sub(' ', s)))

    norm_s = norm(s)
    variants.add(norm_s)
    variants.add(norm_s.replace('-', ''))
    variants.add(norm_s.replace('-', ' '))

    return variants


def company_name_variants(company):
    display_variants = set()  # usable as display name
    matching_variants = set()  # usable for matching

    company = simplify_whitespace(company)

    company = COMPANY_CORRECTIONS.get(company) or company

    m = COMPANY_TYPE_RE.match(company)
    if m:
        company = m.group('company')
        c_type = m.group('type')
        c_type = COMPANY_TYPE_CORRECTIONS.get(c_type) or c_type
        display_variants.add(company + ' ' + c_type)

    display_variants.add(company)

    m = X_AND_CO_RE.match(company)
    if m:
        display_variants.add(m.group('company'))
    else:
        m = THE_X_COMPANY_RE.match(company)
        if m:
            matching_variants.add(m.group('company'))
        else:
            m = X_COMPANY_RE.match(company)
            if m:
                matching_variants.add(m.group('company'))

    normed_variants = set()

    for variants in display_variants, matching_variants:
        for v in variants:
            normed_variants.update(norm_with_variants(v))

    return display_variants, normed_variants


def correct_company_type(c_type):
    if c_type in COMPANY_TYPE_CORRECTIONS:
        return COMPANY_TYPE_CORRECTIONS[c_type]
    elif c_type.endswith('.') and c_type.count('.') == 1:
        return c_type[:-1]
    else:
        return c_type


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
