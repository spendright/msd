# -*- coding: utf-8 -*-
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
import re
from logging import getLogger

from .db import select_groups
from .merge import create_output_table
from .merge import group_by_keys
from .merge import merge_dicts
from .merge import output_row
from .norm import smunch
from .scratch import scratch_tables_with_cols
from .url import match_urls

log = getLogger(__name__)


TM_RE = re.compile('(®|\u2120|™)', re.U)


def build_brand_table(output_db, scratch_db):
    log.info('  building brand table')
    create_output_table(output_db, 'brand')

    brand_sql = (
        'SELECT * from brand'
        ' WHERE scraper_id = ? and company = ? and brand = ?')


    for (company, brand), scraper_map_rows in select_groups(
            output_db, 'scraper_brand_map', ['company', 'brand']):

        tms = {''}  # valid values for tm field
        brand_rows = []  # rows from brand table to merge

        for scraper_map_row in scraper_map_rows:
            tms.add(split_brand_and_tm(scraper_map_row['scraper_brand'])[1])

            for brand_row in scratch_db.execute(
                    brand_sql, [scraper_map_row['scraper_id'],
                                scraper_map_row['scraper_company'],
                                scraper_map_row['scraper_brand']]):
                brand_rows.append(dict(brand_row))
                tms.add(split_brand_and_tm(brand_row['tm'])[1])

        # build final brand row
        brand_row = merge_dicts(
            [dict(company=company, brand=brand)] +
             match_urls(brand_rows, scratch_db) +
             brand_rows)

        # make sure we get a valid value for tm
        brand_row['tm'] = sorted(tms, reverse=True)[0]

        # output it
        output_row(output_db, 'brand', brand_row)


def build_scraper_brand_map_table(output_db, scratch_db):
    log.info('  building scraper_brand_map table')
    create_output_table(output_db, 'scraper_brand_map')

    # TODO: will need to redo this by company family tree
    for (company,), company_map_rows in select_groups(
            output_db, 'scraper_company_map', ['company']):

        scraper_companies = set(
            (row['scraper_id'], row['scraper_company'])
            for row in company_map_rows)

        fill_brands_for_company(
            output_db, scratch_db, company, scraper_companies)


def fill_brands_for_company(output_db, scratch_db, company, scraper_companies):
    # "brand dicts": dicts containing:
    # scraper_brands: set of (scraper_id, scraper_company, scraper_brand)
    # brands: candidates for canonical name of brand
    bds = []

    # get all brand info
    for table_name in scratch_tables_with_cols(['company', 'brand']):
        select_sql = ('SELECT brand FROM `{}`'
                      ' WHERE scraper_id = ? and company = ?'.format(
                          table_name))

        for scraper_id, scraper_company in scraper_companies:
            rows = scratch_db.execute(
                select_sql, [scraper_id, scraper_company])

            for row in rows:
                brand, _ = split_brand_and_tm(row['brand'])
                if brand:
                    bds.append(dict(brands={brand}, scraper_brands={
                        (scraper_id, scraper_company, row['brand'])}))

    # grab company names, to fix capitalization of brand (see #7)
    company_name_sql = (
        'SELECT `company_name` FROM `company_name` where `company` = ?')
    company_names = set(row[0] for row in
                        output_db.execute(company_name_sql, [company]))
    for name in company_names:
        bds.append(dict(brands={name}, scraper_brands=set()))

    # merge brands
    def keyfunc(bd):
        return {smunch(brand) for brand in bd['brands']}

    for bd_group in group_by_keys(bds, keyfunc):
        bd = merge_dicts(bd_group)

        # don't use company names if they don't match real brands
        if not bd['scraper_brands']:
            continue

        brand = pick_brand_name(bd['brands'], company_names)

        for (scraper_id, scraper_company, scraper_brand
             ) in bd['scraper_brands']:
            output_row(output_db, 'scraper_brand_map', dict(
                brand=brand,
                company=company,
                scraper_id=scraper_id,
                scraper_brand=scraper_brand,
                scraper_company=scraper_company))


def select_brands(scratch_db, scraper_companies):
    """Get all possible brand names for the given company(s)."""
    brands = set()

    for scraper_id, scraper_company in scraper_companies:
        for scraper_brand in select_scraper_brands(
                scratch_db, scraper_id, scraper_company):
            brand, _ = split_brand_and_tm(scraper_brand)
            if brand:
                brands.add(brand)

    return brands


def select_scraper_brands(scratch_db, scraper_id, scraper_company):
    """Select all (scraper) brands for the given scraper company."""
    scraper_brands = set()

    for table_name in scratch_tables_with_cols(['company', 'brand']):
        select_sql = ('SELECT brand FROM `{}`'
                      ' WHERE scraper_id = ? and company = ?'.format(
                          table_name))

        for row in scratch_db.execute(
                select_sql, [scraper_id, scraper_company]):
            scraper_brands.add(row[0])

    return scraper_brands


def pick_brand_name(names, company_names=()):
    """Given several versions of a brand name, prefer the one
    that matches a company name, is not all-lowercase,
    not all-uppercase, longest,
    starts with a lowercase letter ("iPhone" > "IPhone"),
    and has the most capital letters ("BlackBerry" > "Blackberry").
    """
    def keyfunc(n):
        return (n not in company_names,
                n != n.lower(),
                n != n.upper(),
                len(n),
                n[0],
                sum(1 for c in n if c.upper() == c))

    return sorted(names, key=keyfunc, reverse=True)[0]


def split_brand_and_tm(scraper_brand):
    """Split apart brand and TM/SM/(R) symbol, discarding anything
    after the symbol."""
    scraper_brand = scraper_brand or ''

    m = TM_RE.search(scraper_brand)
    if m:
        return scraper_brand[:m.start()].strip(), m.group()
    else:
        return scraper_brand.strip(), ''


def map_brand(output_db, scraper_id, scraper_company, scraper_brand):
    """Get the canonical company corresponding to the
    given brand in the scraper data."""
    select_sql = ('SELECT company, brand FROM scraper_brand_map'
                  ' WHERE scraper_id = ? AND scraper_company = ?'
                  ' AND scraper_brand = ?')
    rows = list(output_db.execute(
        select_sql, [scraper_id, scraper_company, scraper_brand]))
    if rows:
        return tuple(rows[0])
    else:
        return None
