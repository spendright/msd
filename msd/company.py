# Copyright 2014-2016 SpendRight, Inc.
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
import re
from collections import defaultdict
from functools import lru_cache
from logging import getLogger

from .company_data import COMPANY_ALIAS_REGEXES
from .company_data import COMPANY_NAME_REGEXES
from .company_data import COMPANY_TYPE_CORRECTIONS
from .company_data import COMPANY_TYPE_RE
from .company_data import UNSTRIPPABLE_COMPANY_TYPES
from .db import select_groups
from .merge import create_output_table
from .merge import group_by_keys
from .merge import merge_dicts
from .merge import output_row
from .norm import norm
from .norm import simplify_whitespace
from .scratch import get_distinct_values
from .url import match_urls

log = getLogger(__name__)


# use this to turn e.g. "babyGap" into "baby Gap" for matching
# this can also turn "G.I. Joe" into "G. I. Joe"
CAMEL_CASE_RE = re.compile('(?<=[a-z\.])(?=[A-Z])')


def build_company_table(output_db, scratch_db):
    log.info('  building company table')
    create_output_table(output_db, 'company')

    company_sql = (
        'SELECT * from company WHERE scraper_id = ? and company = ?')

    company_full_sql = (
        'SELECT company_name FROM company_name WHERE company = ?'
        ' AND is_full = 1')

    for (company,), scraper_map_rows in select_groups(
            output_db, 'scraper_company_map', ['company']):
        company_rows = []

        # get company rows from each scraper
        for scraper_map_row in scraper_map_rows:
            scraper_id = scraper_map_row['scraper_id']
            scraper_company = scraper_map_row['scraper_company']

            company_rows.extend(
                dict(row) for row in
                scratch_db.execute(
                    company_sql, [scraper_id, scraper_company]))

        # get full company name from the company_name table we built
        company_full = list(output_db.execute(
            company_full_sql, [company]))[0][0]

        # build final company row
        company_row = merge_dicts(
            [dict(company=company, company_full=company_full)] +
            match_urls(company_rows, scratch_db) +
            company_rows)

        # output it
        output_row(output_db, 'company', company_row)


def build_company_name_and_scraper_company_map_tables(output_db, scratch_db):
    log.info('  building scraper_company_map and company_name tables')
    create_output_table(output_db, 'scraper_company_map')
    create_output_table(output_db, 'company_name')

    # company dicts ("cds") containing the following sets:
    #
    # names: possible company names
    # aliases: name variants usable for matching (should include *names*)
    # scraper_companies: tuples of (scraper_id, scraper_company)
    cds = []

    cn_cds, invariant_names, sc_to_bad, cn_sc_to_full = (
        load_company_name_corrections(scratch_db))

    cds.extend(cn_cds)

    # populate with any value of 'company' or 'subsidiary' field
    for c_field in ('company', 'subsidiary'):
        for scraper_id, company in (
                get_distinct_values(scratch_db, ['scraper_id', c_field])):

            if not company:
                continue

            cds.append(_make_cd(
                scraper_id, company, company, invariant_names))

    # populate with values of 'company_full' field. these take lower
    # priority than company_name rows tagged with is_full

    cf_sc_to_full = defaultdict(set)

    for scraper_id, company, company_full in (
            get_distinct_values(
                scratch_db, ['scraper_id', 'company', 'company_full'])):

        if not company_full:
            continue  # don't pollute cf_sc_to_full

        cds.append(_make_cd(
            scraper_id, company, company_full, invariant_names))

        cf_sc_to_full[(scraper_id, company)].add(company_full)

    # group together by normed variants of aliases
    def keyfunc(cd):
        keys = set()
        for alias in cd['aliases']:
            keys.update(get_company_keys(alias))
        return keys

    # there are lots of these, so show progress
    for cd_group in group_by_keys(cds, keyfunc):
        cd = merge_dicts(cd_group)

        if not cd['scraper_companies']:
            # this shouldn't happen now; used to happen with
            # hard-coded corrections
            continue

        # promote aliases to display names if they match a brand
        from .brand import select_brands

        brands = select_brands(scratch_db, cd['scraper_companies'])
        normed_brands = {norm(b) for b in brands}
        brand_names = {a for a in cd['aliases'] if norm(a) in normed_brands}

        # look up all scraper companies in a map from scraper company to
        # set, and merge those all into one big set
        def get_names(sc_to_x):
            return {n for sc in cd['scraper_companies'] for n in sc_to_x[sc]}

        # exclude names marked as alias-only
        bad_names = get_names(sc_to_bad)
        names = (cd['names'] | brand_names) - bad_names

        if not names:
            # could happen if only name was flagged as is_alias?
            continue

        # pick company name and full name
        company = pick_company_name(names)

        # pick full name. prioritize names marked is_full in company_name
        # table, then names in company_full field, then other names
        full_names = (get_names(cn_sc_to_full) or
                      get_names(cf_sc_to_full) or
                      names)
        company_full = pick_company_full(full_names)

        # write to scraper_company_map
        for scraper_id, scraper_company in sorted(cd['scraper_companies']):
            output_row(output_db, 'scraper_company_map', dict(
                company=company,
                scraper_id=scraper_id,
                scraper_company=scraper_company))

        # write to company_name

        # company and company_full should always be in cd; just hedging
        company_names = cd['names'] | cd['aliases'] | {company, company_full}

        for company_name in company_names:
            row = dict(company=company, company_name=company_name)

            if company_name == company_full:
                row['is_full'] = 1
            elif company_name not in names:
                row['is_alias'] = 1

            output_row(output_db, 'company_name', row)


def pick_company_name(names):
    # shortest name. Ties broken by not all lower, all upper, has accents
    return sorted(names,
                  key=lambda n: (
                      len(n), n == n.lower(), n != n.upper(),
                      -len(n.encode('utf8'))))[0]


def pick_company_full(names):
    # longest name. Ties broken by, not all lower, all upper, has accents
    return sorted(names,
                  key=lambda n: (
                      -len(n), n == n.lower(), n != n.upper(),
                      -len(n.encode('utf8'))))[0]


def get_company_keys(s):
    variants = set()

    variants.add(norm(CAMEL_CASE_RE.sub(' ', s)))

    norm_s = norm(s)
    variants.add(norm_s)
    variants.add(norm_s.replace('-', ''))
    variants.add(norm_s.replace('-', ' '))
    variants.add(norm_s.replace(' and ', ' & '))
    variants.add(norm_s.replace(' and ', '&'))
    variants.add(norm_s.replace('&', ' & '))
    variants.add(norm_s.replace('&', ' and '))
    variants.add(norm_s.replace('.', ''))
    variants.add(norm_s.replace('.', '. '))
    variants.add(norm_s.replace("'", ''))

    variants = {simplify_whitespace(v) for v in variants}

    # disallow a single character as a key (see #33)
    return {v for v in variants if len(v) > 1}


@lru_cache()
def get_company_names(company):
    """Get a set of possible ways to display company name."""
    return {v for v in _yield_company_names(company) if len(v) > 1}


def _yield_company_names(company):
    # if it's a name like Foo, Inc., allow "Foo" as a display variant
    m = COMPANY_TYPE_RE.match(company)
    if m:
        # process and re-build
        company = m.group('company')
        intl1 = m.group('intl1') or ''
        comma = m.group('comma') or ''
        c_type = m.group('type')
        intl2 = m.group('intl2') or ''
        c_type = COMPANY_TYPE_CORRECTIONS.get(c_type) or c_type
        c_full = company + intl1 + comma + ' ' + c_type + intl2

        yield c_full

        # if the "Inc." etc. is part of the name, stop here
        if c_type in UNSTRIPPABLE_COMPANY_TYPES:
            return

    yield company

    # handle # "The X Co.", "X [&] Co."
    for regex in COMPANY_NAME_REGEXES:
        m = regex.match(company)
        if m:
            name = m.group('company')
            yield name
            break


@lru_cache()
def get_company_aliases(company):
    """Get a set of all ways to match against this company. Some of
    these may be too abbreviated to use as the company's display name."""
    aliases = set()

    # result of get_company_names() is cached, so don't modify it!
    aliases.update(get_company_names(company))

    # Match "The X Company", "X Company", "Groupe X"
    for regex in COMPANY_ALIAS_REGEXES:
        m = regex.match(company)
        if m:
            alias = m.group('company')
            aliases.add(alias)
            break

    # split on slashes
    for a in list(aliases):
        if '/' in a and not COMPANY_TYPE_RE.match(a):  # don't split A/S
            aliases.update((part.strip() for part in a.split('/')))

    # remove short/empty matches
    return {a for a in aliases if len(a) > 1}


def map_company(output_db, scraper_id, scraper_company):
    """Get the canonical company corresponding to the
    given company in the scraper data."""
    select_sql = ('SELECT company FROM scraper_company_map'
                  ' WHERE scraper_id = ? AND scraper_company = ?')
    rows = list(output_db.execute(select_sql, [scraper_id, scraper_company]))
    if rows:
        return rows[0][0]
    else:
        return None


def _make_cd(scraper_id, company, company_name, invariant_names=()):
    """Make a company dict for the given name."""
    if not (scraper_id and company and company_name):
        return dict(aliases=set(), names=set(), scraper_companies=set())

    cd = dict(
        aliases={company, company_name},
        names={company_name},
        scraper_companies={(scraper_id, company)},
    )

    # add variants of company_name
    if company_name not in invariant_names:
        cd['names'].update(get_company_names(company_name))
        cd['aliases'].update(get_company_aliases(company_name))

    # don't worry about variants of *company*; this is handled by making
    # a dict for each value of *company* and then merging them
    # (this is why we need *company* in *aliases*)

    return cd


def load_company_name_corrections(scratch_db):
    """Process the company_name table. Returns
    (cds, invariant_names, sc_to_bad, sc_to_full):

    cds: list of company dicts (see
         build_company_name_and_scraper_company_map_tables())
    invariant_names: set of names that we shouldn't build variants of
    sc_to_bad: map from (scraper_id, company) to an alias that should
         not be a canonical name for that company
    sc_to_full: map from (scraper_id, company) to a name explicitly
         tagged as the company's full name
    """
    # make sure invariant company names get processed first
    sql = 'SELECT * from company_name ORDER BY company'

    cds = []
    invariant_names = set()
    sc_to_bad = defaultdict(set)
    sc_to_full = defaultdict(set)

    for row in scratch_db.execute(sql):
        # special case: invariant company names
        if not row['company']:
            invariant_names.add(row['company_name'])
            continue

        cd = _make_cd(row['scraper_id'], row['company'],
                      row['company_name'], invariant_names)

        sc = (row['scraper_id'], row['company'])

        if row['is_alias']:
            # don't use company_name for naming
            cd['names'] = set()
            sc_to_bad[sc].add(row['company_name'])

        elif row['is_full']:
            sc_to_full[sc].add(row['company_name'])

        cds.append(cd)

    return cds, invariant_names, sc_to_bad, sc_to_full
