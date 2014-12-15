# -*- coding: utf-8 -*-

#   Copyright 2014 SpendRight, Inc.
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
from __future__ import unicode_literals

import logging
import re
from collections import defaultdict

from .brand import get_brands_for_company
from .category import get_brand_categories
from .category import get_company_categories
from .category import get_implied_categories
from .db import output_row
from .db import select_all_companies
from .db import select_brand_claims
from .db import select_brand_ratings
from .db import select_company
from .db import select_company_claims
from .db import select_company_ratings
from .norm import fix_bad_chars
from .norm import group_by_keys
from .norm import norm_with_variants
from .norm import simplify_whitespace
from .rating import merge_ratings
from .url import merge_with_url_data

log = logging.getLogger(__name__)

# various misspellings of company names
COMPANY_CORRECTIONS = {
    'Delta Airlines': 'Delta Air Lines',
    'GEPA- The Fairtrade Company': 'GEPA - The Fairtrade Company',
    'Groupo Modelo S.A.B. de C.V.': 'Grupo Modelo S.A.B. de C.V.',
    'Hanesbrands Incorporated': 'Hanesbrands Inc.',
    'Nescafe': 'Nestlé',  # Nescafé is a brand, not a company
    'PUMA AG Rudolf Dassler Sport': 'Puma SE',
    'SAB Miller': 'SABMiller',
    'V.F. Corporation': 'VF Corporation',
    'Wolverine Worldwide': 'Wolverine World Wide',
    'Woolworths Australia': 'Woolworths Limited',
    'Chocoladefabriken Lindt & Sprungli': 'Lindt & Sprüngli AG',
}

# Name changes. May eventually want separate logic for this.
COMPANY_CORRECTIONS.update({
    'Clean Clothes, Inc.': "Maggie's Functional Organics",
    'Limited Brands': 'L Brands',
    'Limited Brands, Inc.': 'L Brands Inc.',
    'Liz Claiborne': 'Kate Spade & Company',
    'Sweet Earth Chocolates': 'Mama Ganache',  # renamed in 2012
    'RIM': 'BlackBerry Limited', # renamed in 2013
    'Research In Motion': 'BlackBerry Limited',
    'Lindt & Sprüngli GmbH': 'Lindt & Sprüngli AG',  # changed corporate form
})

DEFUNCT_COMPANIES = {
    'Armor Holdings',  # acquired by BAE Systems in 2007, integrated
    'Jones Apparel Group',  # acquired by Nine West Inc.
    'The Jones Group',  # another name for Jones Apparel Group
    'News Corporation',  # split into News Corp, 21st Century Fox
}

COMPANY_ALIASES = [
    ['AB Electrolux', 'Electrolux'],
    ['Anheuser-Busch', 'Anheuser-Busch InBev'],
    ['ASUS', 'ASUSTeK Computer'],
    ['Disney', 'The Walt Disney Company', 'The Walt Disney Co.'],
    ['Gap', 'The Gap'],  # might solve this with "Gap" brand?
    ['GE', 'General Electric'],
    ['HP', 'Hewlett-Packard'],
    ['HTC Electronics', 'HTC'],
    ['Illy', 'illycaffè'],
    ['JetBlue', 'JetBlue Airways'],
    ['Kellogg', "Kellogg's"],  # might solve this with a brand?
    ['L Brands', 'Limited Brands'],
    ['Lindt', 'Lindt & Sprüngli'],
    ['Lidl', 'Lidl Stiftung'],
    ['LG', 'LGE', 'LG Electronics'],
    ['Merck', 'Schering-Plough'],  # merged into Merck
    ['New Look', 'New Look Retailers'],
    ['Philips', 'Royal Philips', 'Royal Philips Electronics'],
    ['PVH', 'Phillips Van Heusen'],
    ['Rivers Australia', 'Rivers (Australia) Pty Ltd'],
    # technically, Wells Fargo Bank, N.A. is a subsidiary of Wells Fargo
    # the multinational. Not worrying about this now and I don't think this is
    # what they meant anyway.
    ['Wells Fargo', 'Wells Fargo Bank'],
    ['Whole Foods', 'Whole Foods Market'],
    ['Wibra', 'Wibra Supermarkt'],
]

# always keep this suffix on the company name
UNSTRIPPABLE_COMPANY_TYPES = {
    'LLP',
}

# don't use the regexes below to shorten these company names
UNSTRIPPABLE_COMPANIES = {
    'Globe International',
    'Woolworths Limited',
}

# don't shorten company names to these
BAD_COMPANY_VARIANTS = {
    'News',  # e.g. News Corporation, News Corp.
}

# "The X Co." -- okay to strip
THE_X_CO_RE = re.compile(
    r'^The (?P<company>.*) Co\.$')

# X [&] Co. -- okay to strip
X_CO_RE = re.compile(
    r'^(?P<company>.*?)( \&)? Co\.$'
)

# regexes for stuff that's okay to strip
COMPANY_DISPLAY_REGEXES = [
    THE_X_CO_RE,
    X_CO_RE,
]


# "The X Company" -- okay for matching, but don't use as short name
THE_X_COMPANY_RE = re.compile(
    r'^The (?P<company>.*) (Co\.|Corporation|Cooperative|Company|Group)$')

# "X Company" -- okay for matching, but don't use as short name
X_COMPANY_RE = re.compile(
    r'^(?P<company>.*) ('
    r'Brands'
    r'|Co.'
    r'|Company'
    r'|Corporation'    r'|Enterprises'
    r'|Group'
    r'|Gruppe'
    r'|Holdings?'
    r'|Products'
    r'|Ventures?'
    r')$'
)

# "Groupe X", etc -- basically the non-English version of X Group
GROUPE_X_RE = re.compile(
    r'^(Groupe'
    r'|Grupo'
    r'|Gruppo'
    r') (?P<company>.*)$'
)

# regexes for pulling out company names that are okay for matching
# but shouldn't automatically qualify to be used as a company's canonical name
COMPANY_MATCHING_REGEXES = [
    THE_X_COMPANY_RE,
    X_COMPANY_RE,
    GROUPE_X_RE,
]

# Inc. etc. -- stuff to strip before even doing the above
COMPANY_TYPE_RE = re.compile(
    r'^(?P<company>.*?)(?P<intl1> International)?,? (?P<type>'
    r'A\.?& S\. Klein GmbH \& Co\. KG'
    r'|A/S'
    r'|AB'
    r'|AG'
    r'|AS'
    r'|ASA'
    r'|Ab'
    r'|BV'
    r'|B\.V\.'
    r'|B.V. Nederland'
    r'|C\.V\.'
    r'|Corp.'
    r'|GmbH \& C[oO]\. [oO]HG'
    r'|GmbH \& Co\. ?KG\.?'  # handle typo: Lukas Meindl GmbH & Co.KG
    r'|GmbH \& Co\. KGaA'
    r'|GmbH'
    r'|Inc\.?'
    r'|Incorporated'
    r'|International'
    r'|KG\.?'
    r'|Llc'
    r'|LLC'
    r'|LLP'
    r'|LP'
    r'|Limited'
    r'|Llp'
    r'|Ltd\.?'
    r'|Ltda\.?'
    r'|nv'
    r'|NV'
    r'|N\.V\.'
    r'|PBC'  # "Public Benefit Corporation"? Only on B Corp site
    r'|PLC'
    r'|P\.C\.'
    r'|Pty\.? Ltd\.?'
    r'|Pty\.?'
    r'|S.\L\.'
    r'|SA'
    r'|SAPI DE CV SOFOM ENR'
    r'|SARL'
    r'|SE'
    r'|S\.A\.?'
    r'|S.A.B. de C.V.'
    r'|S\.A\.U\.'
    r'|S\.R\.L\.'
    r'|S\.p\.A\.'
    r'|Sarl'
    r'|SpA'
    r'|asa'
    r'|b\.v\.'
    r'|gmbh'
    r'|inc\.?'
    r'|plc\.?'
    r')(?P<intl2> International)?$'
)

COMPANY_TYPE_CORRECTIONS = {
    'BV': 'B.V.',
    'Incorporated': 'Inc',
    'Llc': 'LLC',
    'Llp': 'LLP',
    'NV': 'N.V.',
    'S.A': 'S.A.',
    'Sarl': 'SARL',
    'SpA': 'S.p.A.',
    'b.v.': 'B.V.',
    'gmbh': 'GmbH',
    'inc': 'Inc',
    'nv': 'N.V.',
}


def handle_matched_company(cd, category_map, cat_to_ancestors):
    """Take in a company dictionary from match_companies(), and
    output rows about that company to the database.

    This handles writing all rows except for the "campaign" table.

    (or will eventually)
    """
    # TODO: add is_defunct flag instead
    if DEFUNCT_COMPANIES & (cd['display_names'] | cd['matching_names']):
        return

    # get brands
    brand_to_row, brand_map = get_brands_for_company(cd['keys'])

    # pick a canonical name for this company
    company_canonical, company_full = name_company(cd, set(brand_to_row))

    if company_canonical == company_full:
        log.info(company_canonical)
    else:
        log.info('{} ({})'.format(company_canonical, company_full))

    # merge company rows
    company_row = {}

    for scraper_id, company in sorted(cd['keys']):
        company_row.update(select_company(scraper_id, company))

    del company_row['scraper_id']  # should be at least one match

    company_row['company'] = company_canonical
    company_row['company_full'] = company_full

    # store company row
    output_row(company_row, 'company')

    # store company map and ratings
    company_claim_rows = []
    company_rating_rows = []

    for scraper_id, scraper_company in cd['keys']:
        # map
        map_row = dict(
            scraper_id=scraper_id, scraper_company=scraper_company,
            company=company_canonical)
        output_row(map_row, 'scraper_company_map')

        # collect claims
        for row in select_company_claims(scraper_id, scraper_company):
            row['company'] = company_canonical
            company_claim_rows.append(row)

        # collect ratings
        for row in select_company_ratings(scraper_id, scraper_company):
            row['company'] = company_canonical
            company_rating_rows.append(row)

    # merge and index company rating rows
    company_rating_rows = list(merge_ratings(company_rating_rows))
    cs_to_row = dict(((row['company'], row['scope']), row)
                     for row in company_rating_rows)

    # output company claims
    for company_claim_row in company_claim_rows:
        # skip "claims" that don't support a judgment
        if company_claim_row.get('judgment') is None:
            continue

        # if claim doesn't have a URL, patch in rating's URL
        rating_row = cs_to_row.get((company_claim_row['company'],
                                    company_claim_row['scope']))

        if rating_row and not company_claim_row.get('url'):
            company_claim_row['url'] = rating_row.get('url')

        output_row(company_claim_row, 'campaign_company_claim')

    # output company ratings
    for company_rating_row in company_rating_rows:
        output_row(company_rating_row, 'campaign_company_rating')

    # store company categories
    company_cats = set()
    for cat_row in get_company_categories(
            company_canonical, cd['keys'], category_map):
        company_cats.add(cat_row['category'])
        output_row(cat_row, 'company_category')

    for implied_cat in get_implied_categories(company_cats, cat_to_ancestors):
        output_row(dict(company=company_canonical, category=implied_cat,
                        is_implied=1),
                   'company_category')

    # store brands
    brand_rows = sorted(brand_to_row.itervalues(), key=lambda r: r['brand'])
    for brand_row in brand_rows:
        brand_row['company'] = company_canonical
        output_row(brand_row, 'brand')

    # store brand map, rating
    scraper_to_company = dict(cd['keys'])
    brand_to_keys = defaultdict(set)
    brand_claim_rows = []
    brand_rating_rows = []

    for (scraper_id, scraper_brand), brand_canonical in brand_map.items():
        scraper_company = scraper_to_company[scraper_id]

        brand_to_keys[brand_canonical].add(
            (scraper_id, scraper_company, scraper_brand))

        # map
        map_row = dict(
            scraper_id=scraper_id, scraper_company=scraper_company,
            scraper_brand=scraper_brand, company=company_canonical,
            brand=brand_canonical)
        output_row(map_row, 'scraper_brand_map')

        # collect ratings
        for row in select_brand_claims(
                scraper_id, scraper_company, scraper_brand):
            row['company'] = company_canonical
            row['brand'] = brand_canonical
            brand_claim_rows.append(row)

        # collect ratings
        for row in select_brand_ratings(
                scraper_id, scraper_company, scraper_brand):
            row['company'] = company_canonical
            row['brand'] = brand_canonical
            brand_rating_rows.append(row)

    # merge and index brand rating rows
    brand_rating_rows = list(merge_ratings(brand_rating_rows))
    cbs_to_row = dict(((row['company'], row['brand'], row['scope']), row)
                      for row in brand_rating_rows)

    # output brand claims
    for brand_claim_row in brand_claim_rows:
        # skip "claims" that don't support a judgment
        if brand_claim_row.get('judgment') is None:
            continue

        # if claim doesn't have a URL, patch in rating's URL
        rating_row = cbs_to_row.get((brand_claim_row['company'],
                                     brand_claim_row['brand'],
                                     brand_claim_row['scope']))

        if rating_row and not brand_claim_row.get('url'):
            brand_claim_row['url'] = rating_row.get('url')

        output_row(brand_claim_row, 'campaign_brand_claim')

    # output brand ratings
    for brand_rating_row in brand_rating_rows:
        output_row(brand_rating_row, 'campaign_brand_rating')

    # store brand categories
    brand_cats = set()
    for brand_canonical, keys in sorted(brand_to_keys.items()):
        for cat_row in get_brand_categories(
                company_canonical, brand_canonical, keys, category_map):
            brand_cats.add(cat_row['category'])
            output_row(cat_row, 'brand_category')

    for implied_cat in get_implied_categories(brand_cats, cat_to_ancestors):
        output_row(dict(company=company_canonical, brand=brand_canonical,
                        category=implied_cat, is_implied=1),
                   'brand_category')


def name_company(cd, brands=()):
    """Return short and full names for a company."""
    short_name = pick_short_name_from_variants(cd['display_names'])

    # if matching short name is shorter and matches a brand for one
    # of the companies, use that
    if brands:
        matching_short_name = pick_short_name_from_variants(
            cd['display_names'] | cd['matching_names'])

        if matching_short_name != short_name:
            # use normed variants so that e.g. "ASICS" matches "Asics"
            msn_nvs = norm_with_variants(matching_short_name)
            brand_nvs = set(v for brand in brands
                                 for v in norm_with_variants(brand))

            if msn_nvs & brand_nvs:
                short_name = matching_short_name

    full_name = pick_full_name_from_variants(cd['display_names'])

    return short_name, full_name


def match_companies(companies_with_scraper_ids=None, aliases=None):
    """Match up similar company names.

    companies -- sequence of (scraper_id, company). Defaults to
                 get_companies_with_scraper_ids()
    aliases -- sequence of list of matching company names. Defaults to
               COMPANY_ALIASES

    Yields company dicts, which contain:
    keys -- set of tuples of (scraper_id, original_company_name)
    display_names -- set of names appropriate for display
    matching_names -- set of names for matching
    """
    if companies_with_scraper_ids is None:
        companies_with_scraper_ids = select_all_companies()
    if aliases is None:
        aliases = COMPANY_ALIASES

    to_merge = []

    # use variants for matching
    for variants in aliases:
        variants = set(variants)
        to_merge.append({'keys': set(), 'display_names': set(),
                         'matching_names': variants})

    # add in companies
    for scraper_id, company in companies_with_scraper_ids:
        if not company:  # skip blank company names
            continue

        keys = {(scraper_id, company)}

        display, matching = get_company_name_variants(company)

        to_merge.append({'keys': keys, 'display_names': set(display),
                         'matching_names': set(matching)})

    # match up company dicts and merge them together
    def keyfunc(cd):
        normed_variants = set()
        for name in cd['matching_names']:
            normed_variants.update(norm_with_variants(name))
        return normed_variants

    # and merge them together
    for cd_group in group_by_keys(to_merge, keyfunc):
        merged = merge_with_url_data(cd_group)

        if not (merged['keys'] and merged['display_names']):
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
    company = fix_bad_chars(company)

    display_variants = set()  # usable as display name
    matching_variants = set()  # usable for matching

    # putting this in a sub-function so we can bail out easily with "return"
    def handle(company):
        company = simplify_whitespace(company)

        company = COMPANY_CORRECTIONS.get(company) or company

        # if it's a name like Foo, Inc., allow "Foo" as a display variant
        m = COMPANY_TYPE_RE.match(company)
        if m and m.group('company') not in BAD_COMPANY_VARIANTS:
            company = m.group('company')
            intl1 = m.group('intl1') or ''
            c_type = m.group('type')
            intl2 = m.group('intl2') or ''
            c_type = COMPANY_TYPE_CORRECTIONS.get(c_type) or c_type
            c_full = company + intl1 + ' ' + c_type + intl2
            display_variants.add(c_full)

            # if the "Inc." etc. is part of the name, stop here
            if (c_type in UNSTRIPPABLE_COMPANY_TYPES or
                c_full in UNSTRIPPABLE_COMPANIES):
                return

        # at this point, company is either the original name, or
        # the name with "Inc." etc. stripped off
        display_variants.add(company)

        # add one more variant, which may be for matching only. This
        # handles things that are less obviously corporate suffixes, like
        # "& Co." and "Group"
        for regexes, dest in ((COMPANY_DISPLAY_REGEXES, display_variants),
                              (COMPANY_MATCHING_REGEXES, matching_variants)):
            for regex in regexes:
                m = regex.match(company)
                if m:
                    variant = m.group('company')
                    if variant not in BAD_COMPANY_VARIANTS:
                        dest.add(variant)
                        return

    handle(company)

    # display variants are always good for matching too
    matching_variants.update(display_variants)

    # handle slashes in company names
    for mv in list(matching_variants):
        if '/' in mv and not COMPANY_TYPE_RE.match(mv):  # don't split A/S
            matching_variants.update(
                filter(None, (part.strip() for part in mv.split('/'))))

    # don't allow single-character names (would also catch A/S)
    display_variants = set(dv for dv in display_variants if len(dv) > 1)
    matching_variants = set(mv for mv in matching_variants if len(mv) > 1)

    return display_variants, matching_variants


def correct_company_type(c_type):
    if c_type in COMPANY_TYPE_CORRECTIONS:
        return COMPANY_TYPE_CORRECTIONS[c_type]
    elif c_type.endswith('.') and c_type.count('.') == 1:
        return c_type[:-1]
    else:
        return c_type
