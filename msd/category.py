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
from logging import getLogger

from .category_data import BAD_CATEGORIES
from .category_data import USELESS_CATEGORY_SUFFIXES
from .category_data import CATEGORY_ALIASES
from .category_data import CATEGORY_SPLITS
from .db import select_groups
from .merge import create_output_table
from .merge import output_row
from .norm import simplify_whitespace
from .norm import to_title_case
from .scratch import get_distinct_values
from .target import select_groups_by_target


log = getLogger(__name__)

CATEGORY_SPLIT_RE = re.compile(r',?\s+and\s+|,\s+|\.\s+|\s*/\s*')


def build_category_table(output_db, scratch_db):
    log.info('  building category table')
    create_output_table(output_db, 'category')

    for (company, brand), _, category_rows in select_groups_by_target(
            output_db, scratch_db, 'category'):

        # map categories from rows
        categories = set()
        for category_row in category_rows:
            category = map_category(output_db,
                                    category_row['scraper_id'],
                                    category_row['category'])
            if category:
                categories.add(category)

        implied_categories = get_implied_categories(output_db, categories)

        for category in sorted(categories | implied_categories):
            output_row(output_db, 'category', dict(
                company=company,
                brand=brand,
                category=category,
                is_implied=category not in categories))


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

    # map from category to {subcategories}
    cat_to_subcats = defaultdict(set)
    # tuples of (category, subcategory)
    direct_subcategories = set()

    # read and translate subcategory table
    for (scraper_id, scraper_category, scraper_subcategory), rows in (
            select_groups(scratch_db, 'subcategory',
                          ['scraper_id', 'category', 'subcategory'])):
        category = map_category(output_db, scraper_id, scraper_category)
        subcategory = map_category(output_db, scraper_id, scraper_subcategory)
        if not (category and subcategory):
            continue

        cat_to_subcats[category].add(subcategory)
        if any(not row.get('is_implied') for row in rows):
            direct_subcategories.add((category, subcategory))

    # split "and" categories
    cat_sql = 'SELECT DISTINCT category from scraper_category_map'
    for row in output_db.execute(cat_sql):
        category = row[0]
        for subcategory in split_category(category):
            cat_to_subcats[category].add(subcategory)
            direct_subcategories.add((category, subcategory))

    # imply subcategories
    cat_to_ancestors = _imply_category_ancestors(cat_to_subcats)

    # output rows
    for cat, ancestors in sorted(cat_to_ancestors.items()):
        for ancestor in sorted(ancestors):
            subcat_row = {'category': ancestor, 'subcategory': cat}
            if (ancestor, cat) not in direct_subcategories:
                subcat_row['is_implied'] = 1

            output_row(output_db, 'subcategory', subcat_row)


def _imply_category_ancestors(cat_to_subcats):
    cat_to_ancestors = defaultdict(set)
    active_cats = set(cat_to_subcats)

    while active_cats:
        next_active_cats = set()

        for active_cat in active_cats:
            children = cat_to_subcats.get(active_cat, ())
            for child in children:
                # don't make anything ancestor of itself
                to_propogate = (
                    {active_cat} | cat_to_ancestors[active_cat]) - {child}
                child_ancestors = cat_to_ancestors[child]

                if to_propogate - child_ancestors:
                    cat_to_ancestors[child] |= to_propogate
                    next_active_cats.add(child)

        active_cats = next_active_cats

    return dict((cat, ancestors)
                for cat, ancestors in cat_to_ancestors.items()
                if ancestors)



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


def split_category(category):
    """Determine subcategories of the given (normalized) category."""
    if category in CATEGORY_SPLITS:
        return CATEGORY_SPLITS[category]
    elif CATEGORY_SPLIT_RE.search(category):
        return set(
            CATEGORY_ALIASES.get(part, part)
            for part in CATEGORY_SPLIT_RE.split(category))
    else:
        return set()


def get_implied_categories(output_db, subcategories):
    """Get a set of categories implied by the given subcategories."""
    if not subcategories:
        return set()

    subcategories = list(subcategories)

    select_sql = ('SELECT DISTINCT `category` from `subcategory`'
                  ' WHERE `subcategory` IN ({})').format(
                      ', '.join('?' for _ in range(len(subcategories))))

    return {row[0] for row in output_db.execute(select_sql, subcategories)}
