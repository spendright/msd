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
from logging import getLogger

from .category_data import BAD_CATEGORIES
from .category_data import USELESS_CATEGORY_SUFFIXES
from .category_data import CATEGORY_ALIASES
from .merge import create_output_table
from .merge import output_row
from .norm import simplify_whitespace
from .norm import to_title_case
from .scratch import get_distinct_values

log = getLogger(__name__)


def build_category_table(output_db, scratch_db):
    log.info('  building category table')
    create_output_table(output_db, 'category')
    log.warning('  filling category table not yet implemented')


def build_scraper_category_map_table(output_db, scratch_db):
    log.info('  building scraper_category_map table')
    create_output_table(output_db, 'scraper_category_map')

    # a category exists if it's named as a category or a subcategory
    scraper_cats = (
        get_distinct_values(scratch_db, ['scraper_id', 'category']) |
        get_distinct_values(scratch_db, ['scraper_id', 'subcategory']))

    for scraper_id, scraper_category in scraper_cats:
        # derive canonical category from scraper category
        category = fix_category(scraper_category)
        if not category:
            continue

        # output mapping
        output_row(output_db, 'scraper_category_map', dict(
            category=category,
            scraper_category=scraper_category,
            scraper_id=scraper_id))


def build_subcategory_table(output_db, scratch_db):
    log.info('  building subcategory table')
    create_output_table(output_db, 'subcategory')
    log.warning('  filling subcategory table not yet implemented')


def map_category(output_db, scraper_id, scraper_category):
    """Get the canonical category corresponding to the
    given category in the scraper data."""
    select_sql = ('SELECT category FROM scraper_category_map'
                  ' WHERE scraper_id = ? AND scraper_category = ?')
    rows = list(output_db.execute(select_sql, [scraper_id, scraper_category]))
    if rows:
        return rows[0][0]
    else:
        return None


def fix_category(category):
    category = category.replace('&', ' and ')
    category = simplify_whitespace(category)
    category = to_title_case(category)

    for suffix in USELESS_CATEGORY_SUFFIXES:
        if category.endswith(suffix):
            category = category[:-len(suffix)]
            break

    if not category or category in BAD_CATEGORIES:
        return None

    elif category in CATEGORY_ALIASES:
        return CATEGORY_ALIASES[category]

    else:
        return category
