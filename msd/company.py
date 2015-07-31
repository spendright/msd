# Copyright 2014-2015 SpendRight, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from functools import lru_cache
from logging import getLogger

from .company_data import BAD_COMPANY_VARIANTS
from .company_data import COMPANY_CORRECTIONS
from .company_data import COMPANY_DISPLAY_REGEXES
from .company_data import COMPANY_MATCHING_REGEXES
from .company_data import COMPANY_TYPE_CORRECTIONS
from .company_data import COMPANY_TYPE_RE
from .company_data import UNSTRIPPABLE_COMPANIES
from .company_data import UNSTRIPPABLE_COMPANY_TYPES


from .merge import create_output_table

log = getLogger(__name__)


def build_company_table(output_db, scratch_db):
    log.info('  building company table')
    create_output_table(output_db, 'company')
    log.warning('  filling company table not yet implemented')


def build_scraper_company_map_table(output_db, scratch_db):
    log.info('  building scraper_company_map table')
    create_output_table(output_db, 'scraper_company_map')

    pass


@lru_cache(maxsize=1)
def get_company_display_variants(company):
    """Get a set of possible ways to display company name."""
    return set(v for v in _yield_company_display_variants(company)
               if len(v) > 1)


def _yield_company_display_variants(company):
    company = COMPANY_CORRECTIONS.get(company) or company

    # if it's a name like Foo, Inc., allow "Foo" as a display variant
    m = COMPANY_TYPE_RE.match(company)
    if m and m.group('company') not in BAD_COMPANY_VARIANTS:
        # process and re-build
        company = m.group('company')
        intl1 = m.group('intl1') or ''
        c_type = m.group('type')
        intl2 = m.group('intl2') or ''
        c_type = COMPANY_TYPE_CORRECTIONS.get(c_type) or c_type
        c_full = company + intl1 + ' ' + c_type + intl2

        yield c_full

        # if the "Inc." etc. is part of the name, stop here
        if (c_type in UNSTRIPPABLE_COMPANY_TYPES or
            c_full in UNSTRIPPABLE_COMPANIES):
            return

    yield company

    # handle # "The X Co.", "X [&] Co."
    for regex in COMPANY_DISPLAY_REGEXES:
        m = regex.match(company)
        if m:
            variant = m.group('company')
            if variant not in BAD_COMPANY_VARIANTS:
                yield variant
                break


def get_company_matching_variants(company):
    """Get a set of all ways to match against this company. Some of
    these may be too abbreviated to use as the company's display name."""
    variants = get_company_display_variants()

    # Match "The X Company", "X Company", "Groupe X"
    for regex in COMPANY_MATCHING_REGEXES:
        m = regex.match(company)
        if m:
            variant = m.group('company')
            if variant not in BAD_COMPANY_VARIANTS:
                variants.add(variant)
                break

    # split on slashes
    for v in list(variants):
        if '/' in v and not COMPANY_TYPE_RE.match(v):  # don't split A/S
            variants.update((part.strip() for part in v.split('/')))

    # remove short/empty matches
    return set(v for v in variants if len(v) > 1)
