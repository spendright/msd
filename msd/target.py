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
"""Utilities for targets, which can be either companies or brands."""
from collections import defaultdict

from .brand import map_brand
from .company import map_company
from .db import select_groups


def map_target(output_db, scraper_id, scraper_company, scraper_brand=''):
    """Map either a company or brand, returning a tuple of
    (company, brand), or None if no match."""
    if scraper_brand:
        return map_brand(output_db, scraper_id, scraper_company, scraper_brand)
    else:
        company = map_company(output_db, scraper_id, scraper_company)
        if company is None:
            return None
        else:
            return (company, '')


def select_groups_mapped_by_target(output_db, scratch_db, table_name, keyfunc):
    """Yield lists of rows from the scratch DB corresponding to the same
    company, brand, and key (the result of keyfunc(row)).

    company and brand in the rows returned will the the canonical,
    company/brand, not the values in the scratch DB.
    """
    for (company, brand), target_map_rows in _select_target_groups(output_db):
        key_to_rows = defaultdict(list)

        for row in _select_and_map_by_targets(
                scratch_db, table_name, target_map_rows):

            key = keyfunc(row)
            key_to_rows[key].append(row)

        for key, row_group in key_to_rows.items():
            yield key, row_group


def _select_target_groups(output_db):
    """Yield tuples of (company, brand), brand_map_row for all companies
    and brands."""
    # yield all brand mapping
    for (company, brand), brand_map_rows in select_groups(
            output_db, 'scraper_brand_map', ['company', 'brand']):
        yield (company, brand), brand_map_rows

    # now do companies, adding in missing brand fields
    for (company,), company_map_rows in select_groups(
            output_db, 'scraper_company_map', ['company']):
        yield (company, ''), [dict(
            brand='',
            company=company,
            scraper_brand='',
            scraper_company=r['scraper_company'],
            scraper_id=r['scraper_id'],
        ) for r in company_map_rows]


def _select_and_map_by_targets(scratch_db, table_name, target_map_rows):
    select_sql = (
        'SELECT * FROM `{}` WHERE scraper_id = ? AND'
        ' company = ? AND brand = ?'.format(table_name))

    for target_map_row in target_map_rows:
        for row in scratch_db.execute(
                select_sql, [target_map_row['scraper_id'],
                             target_map_row['scraper_company'],
                             target_map_row['scraper_brand']]):

            row = dict(row)
            row['company'] = target_map_row['company']
            row['brand'] = target_map_row['brand']

            yield row
