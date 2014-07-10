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
"""Merge and correct company information."""
import re
from collections import defaultdict
from itertools import groupby
from unidecode import unidecode

from .db import open_db


# various misspellings of company names
COMPANY_CORRECTIONS = {
    'GEPA- The Fairtrade Company': 'GEPA - The Fairtrade Company',
    'V.F. Corporation': 'VF Corporation',
    'Wolverine Worldwide': 'Wolverine World Wide',
    'Woolworths Australia': 'Woolworths Limited',
}

COMPANY_ALIASES = [
    ['AB Electrolux', 'Electrolux'],
    ['Disney', 'The Walt Disney Company', 'The Walt Disney Co.'],
    ['HP', 'Hewlett-Packard'],
    ['LG', 'LGE', 'LG Electronics'],
    ['Rivers Australia', 'Rivers (Australia) Pty Ltd'],
    # technically, Wells Fargo Bank, N.A. is a subsidiary of Wells Fargo
    # the multinational. Not worrying about this now and I don't think this is
    # what they meant anyway.
    ['Wells Fargo', 'Wells Fargo Bank'],
    ['Whole Foods', 'Whole Foods Market'],
    ['Wibra', 'Wibra Supermarkt'],
]


# "The X Co." -- okay to strip
THE_X_CO_RE = re.compile(
    r'^The (?P<company>.*) Co\.$')

# X [&] Co. -- okay to strip
X_CO_RE = re.compile(
    r'^(?P<company>.*)( \&)? Co\.$'
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
    r'|Holdings'
    r'|Ventures?'
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
    r'|Incorporated'
    r'|KG\.?'
    r'|Llc'
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
    r'|Sarl'
    r'|SE'
    r'|S\.A\.?'
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
    'Incorporated': 'Inc',
    'Llc': 'LLC',
    'Llp': 'LLP',
    'NV': 'N.V.',
    'S.A': 'S.A.',
    'Sarl': 'SARL',
    'b.v.': 'B.V.',
    'gmbh': 'GmbH',
    'inc': 'Inc',
}

UNSTRIPPABLE_COMPANY_TYPES = {
    'LLP',
}

UNSTRIPPABLE_COMPANIES = {
    'Woolworths Limited'
}


# use this to turn e.g. "babyGap" into "baby Gap"
# this can also turn "G.I. Joe" into "G. I. Joe"
CAMEL_CASE_RE = re.compile('(?<=[a-z\.])(?=[A-Z])')

# use to remove excess whitespace
WHITESPACE_RE = re.compile(r'\s+')



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


def name_matched_company(cd):
    """Take a company dictionary from match_companies, and return
    a dict with the keys 'company' (a short name, used as a key),
    'company_full' (a long, corporate version of the name),
    and 'keys' (a list of tuples of (campaign_id, company_in_campaign))
    """
    short_name = pick_short_name_from_variants(cd['display'])

    # if matching short name is shorter and matches a brand for one
    # of the companies, use that
    matching_short_name = pick_short_name_from_variants(
        cd['display'] | cd['matching'])

    if (matching_short_name != short_name and
        brand_exists(matching_short_name, cd['keys'])):
        short_name = matching_short_name

    full_name = pick_full_name_from_variants(cd['display'])

    return dict(
        company=short_name,
        company_full=full_name,
        keys=tuple(cd['keys']))




def match_companies(companies_with_campaign_ids=None, aliases=None):
    """Match up similar company names.

    companies -- sequence of (company, [campaign_ids]). Defaults to
                 get_companies_with_campaign_ids()
    aliases -- sequence of list of matching company names. Defaults to
               COMPANY_ALIASES
    """
    if companies_with_campaign_ids is None:
        companies_with_campaign_ids = get_companies_with_campaign_ids()
    if aliases is None:
        aliases = COMPANY_ALIASES

    nv2cd = {}  # normed variant to company dictionary

    def add(display, matching, keys=()):
        # figure out normed variants, for merging
        normed = set()
        for mv in matching:
            normed.update(norm_with_variants(mv))

        company = dict(keys=set(keys), display=set(display),
                       matching=set(matching),
                       normed=normed)

        # merge other company entries into our own
        for nv in sorted(normed):
            if nv in nv2cd:
                for k in company:
                    company[k] |= nv2cd[nv][k]

        for nv in normed:
            nv2cd[nv] = company

    # company dictionaries have these fields:
    # keys: set of tuples of (campaign_id, company) (original company name)
    # display: set of names appropriate for display
    # matching: set of names appropriate for matching but probably not display
    # normed: set of normed company name variants

    # handle aliases
    for variants in aliases:
        add(display=variants, matching=variants)

    # handle real companies
    for company, campaign_ids in companies_with_campaign_ids:
        if not company:  # skip blank company names
            continue
        display, matching = get_company_name_variants(company)
        add(display, matching,
            keys=[(campaign_id, company) for campaign_id in campaign_ids])

    # yield unique company dictionaries
    ids_seen = set()
    for cd in nv2cd.itervalues():
        if id(cd) not in ids_seen:
            yield cd
            ids_seen.add(id(cd))


def pick_short_name_from_variants(variants):
    # shortest name, ties broken by, not all lower/upper, has accents
    return sorted(variants,
                  key=lambda v: (len(v), v == v.lower(), v == v.upper(),
                                 -len(v.encode('utf8'))))[0]

def pick_full_name_from_variants(variants):
    # longest name, ties broken by, not all lower/upper, has accents
    return sorted(variants,
                  key=lambda v: (-len(v), v == v.lower(), v == v.upper(),
                                 -len(v.encode('utf8'))))[0]


def get_company_name_variants(company):
    """Convert a company name to a set of variants for display,
    and a set of variants for matching only.
    """

    display_variants = set()  # usable as display name
    matching_variants = set()  # usable for matching

    def handle(company):
        company = simplify_whitespace(company)

        company = COMPANY_CORRECTIONS.get(company) or company

        m = COMPANY_TYPE_RE.match(company)
        if m:
            company = m.group('company')
            c_type = m.group('type')
            c_type = COMPANY_TYPE_CORRECTIONS.get(c_type) or c_type
            c_full = company + ' ' + c_type
            display_variants.add(c_full)

            if (c_type in UNSTRIPPABLE_COMPANY_TYPES or
                c_full in UNSTRIPPABLE_COMPANIES):
                return

        display_variants.add(company)

        m = THE_X_CO_RE.match(company)
        if m:
            display_variants.add(m.group('company'))
            return

        m = X_CO_RE.match(company)
        if m:
            display_variants.add(m.group('company'))
            return

        m = THE_X_COMPANY_RE.match(company)
        if m:
            matching_variants.add(m.group('company'))
            return

        m = X_COMPANY_RE.match(company)
        if m:
            matching_variants.add(m.group('company'))
            return

    handle(company)

    matching_variants |= display_variants

    return display_variants, matching_variants


def correct_company_type(c_type):
    if c_type in COMPANY_TYPE_CORRECTIONS:
        return COMPANY_TYPE_CORRECTIONS[c_type]
    elif c_type.endswith('.') and c_type.count('.') == 1:
        return c_type[:-1]
    else:
        return c_type


def get_companies_with_campaign_ids():
    campaigns_db = open_db('campaigns')

    cursor = campaigns_db.execute(
        'SELECT company, campaign_id from campaign_company'
        ' ORDER BY company')

    for company, rows in groupby(cursor, key=lambda row: row['company']):
        yield company, set(row['campaign_id'] for row in rows)


def brand_exists(brand, keys):
    campaigns_db = open_db('campaigns')

    for campaign_id, company in keys:
        rows = list(campaigns_db.execute(
            'SELECT 1 FROM campaign_brand WHERE campaign_id = ?'
            ' AND company = ? AND brand = ?', [campaign_id, company, brand]))
        if rows:
            return True

    return False
