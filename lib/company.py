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
    ['Coca-Cola', 'The Coca-Cola Company'],
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


def match_company_names(companies, aliases=None):
    """Match up similar company names."""
    nv2dvs = defaultdict(set)  # normed variant to display variants
    nv2origs = defaultdict(set)  # normed variant to original names
    nv2nvs = {} # normed variant to set of matched variants including itself

    if aliases is None:
        aliases = COMPANY_ALIASES

    for dvs in COMPANY_ALIASES:
        nvs = set()
        for dv in dvs:
            for nv in norm_with_variants(dv):
                nv2dvs[nv].add(dv)
                nvs.add(nv)

        # put all normed variants in same set
        merge_sets(nv2nvs, nvs)

    for orig in companies:
        if not orig:
            continue
        dvs, nvs = company_name_variants(orig)
        for nv in nvs:
            nv2dvs[nv].update(dvs)
            nv2origs[nv].add(orig)
        merge_sets(nv2nvs, nvs)

    sn2info = {}  # short name to 'companies', 'company_full'

    seen_ids = set()
    for nvs in nv2nvs.itervalues():
        if id(nvs) in seen_ids:
            continue
        seen_ids.add(id(nvs))

        dvs = set()
        for nv in nvs:
            dvs.update(nv2dvs[nv])

        sn, company_full = pick_short_and_full_company_name(dvs)

        companies = set()
        for nv in nvs:
            companies.update(nv2origs[nv])

        sn2info[sn] = {
            'companies': companies,
            'company_full': company_full,
        }

    return sn2info


def pick_short_and_full_company_name(variants):
    if not variants:
        raise ValueError('need at least one company name')

    # shortest name, ties broken by, not all lower/upper, has acceents
    short_name = sorted(variants,
                        key=lambda v: (len(v), v == v.lower(), v == v.upper(),
                                       -len(v.encode('utf8'))))[0]

    # longest name, ties broken by, not all lower/upper, has acceents
    full_name = sorted(variants,
                       key=lambda v: (-len(v), v != v.lower(), v != v.upper(),
                                      -len(v.encode('utf8'))))[0]

    return short_name, full_name







def company_name_variants(company):
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

    normed_variants = set()
    for variants in display_variants, matching_variants:
        for variant in variants:
            normed_variants.update(norm_with_variants(variant))

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
            elt_to_set[e] = {e}

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
