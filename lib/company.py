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
import logging
import re
from itertools import groupby
from unidecode import unidecode

from .brand import get_brand_to_row
from .db import open_db
from .db import open_output_dump_truck
from .db import select_campaign_company
from .norm import group_by_keys

log = logging.getLogger(__name__)

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



def handle_matched_company(cd):
    """Take in a company dictionary from match_companies(), and
    output rows about that company to the database.

    This handles writing all rows except for the "campaign" table.

    (or will eventually)
    """
    dt = open_output_dump_truck()

    # get brands
    brand_to_row = get_brand_to_row(cd['keys'])

    # pick a canonical name for this company
    short_name, full_name = name_company(cd, set(brand_to_row))

    # merge company rows
    company_row = {}

    for campaign_id, company in sorted(cd['keys']):
         company_row.update(select_campaign_company(campaign_id, company))

    del company_row['campaign_id']   # should be at least one match!

    company_row['company'] = short_name
    company_row['company_full'] = full_name

    # store company row
    dt.upsert(company_row, 'company')

    # store brands
    brand_rows = sorted(brand_to_row.itervalues(), key=lambda r: r['brand'])
    for brand_row in brand_rows:
        brand_row['company'] = short_name
        dt.upsert(brand_row, 'brand')

    # put brands into company row (for debugging)
    company_record = company_row
    company_record['brands'] = brand_rows

    return company_record



def name_company(cd, brands=()):
    """Return short and full names for a company."""
    short_name = pick_short_name_from_variants(cd['display_names'])

    # if matching short name is shorter and matches a brand for one
    # of the companies, use that
    matching_short_name = pick_short_name_from_variants(
        cd['display_names'] | cd['matching_names'])

    if (matching_short_name != short_name and
        matching_short_name in brands):
        short_name = matching_short_name

    full_name = pick_full_name_from_variants(cd['display_names'])

    return short_name, full_name


def match_companies(companies_with_campaign_ids=None, aliases=None):
    """Match up similar company names.

    companies -- sequence of (company, [campaign_ids]). Defaults to
                 get_companies_with_campaign_ids()
    aliases -- sequence of list of matching company names. Defaults to
               COMPANY_ALIASES

    Yields company dicts, which contain:
    keys -- set of tuples of (campaign_id, original_company_name)
    display_names -- set of names appropriate for display
    matching_names -- set of names for matching
    """
    if companies_with_campaign_ids is None:
        companies_with_campaign_ids = get_companies_with_campaign_ids()
    if aliases is None:
        aliases = COMPANY_ALIASES

    to_merge = []

    # use variants for matching
    for variants in aliases:
        variants = set(variants)
        to_merge.append({'keys': set(), 'display_names': set(),
                         'matching_names': variants})

    # add in companies
    for company, campaign_ids in companies_with_campaign_ids:
        if not company:  # skip blank company names
            continue
        keys=set((campaign_id, company) for campaign_id in campaign_ids)
        display, matching = get_company_name_variants(company)

        to_merge.append({'keys': keys, 'display_names': set(display),
                         'matching_names': set(matching)})

    # match up company dicts
    def keyfunc(cd):
        normed_variants = set()
        for name in cd['matching_names']:
            normed_variants.update(norm_with_variants(name))
        return normed_variants

    # and merge them together
    for cd_group in group_by_keys(to_merge, keyfunc):
        merged = {'keys': set(), 'display_names': set(),
                  'matching_names': set()}
        for cd in cd_group:
            for k in merged:
                merged[k].update(cd[k])

        if not merged['keys'] and merged['display_names']:
            # this can happen if hard-coded variants don't match anything
            log.warn('orphaned company dict: {}'.format(repr(merged)))
        else:
            yield merged


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

    matching_variants.update(display_variants)

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
