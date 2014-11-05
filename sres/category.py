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
"""Utilities for category information."""
import logging
from collections import defaultdict

from .db import output_row
from .db import select_categories
from .db import select_brand_categories
from .db import select_company_categories
from .norm import fix_bad_chars
from .norm import group_by_keys
from .norm import merge_dicts
from .norm import simplify_whitespace
from .norm import to_title_case


# too vague to be useful
BAD_CATEGORIES = {
    'Commercial Products',
    'Industry Innovators',
    'Other',
}

# not useful
BAD_SUFFIXES = [
    ' Brands',
    ' Products',
]

log = logging.getLogger(__name__)


def fix_category(category, scraper_id):
    category = fix_bad_chars(category)
    category = category.replace('&', ' and ')
    category = simplify_whitespace(category)
    category = to_title_case(category)

    for suffix in BAD_SUFFIXES:
        if category.endswith(suffix):
            category = category[:-len(suffix)]
            break

    if not category or category in BAD_CATEGORIES:
        return None
    else:
        return category


def get_category_map():
    key_to_category = {}

    for row in select_categories():
        category = fix_category(row['category'], row['scraper_id'])
        if category is None:
            continue

        key_to_category[(row['scraper_id'], row['category'])] = category

    return key_to_category


def output_scraper_category_map(category_map):
    category_to_keys = defaultdict(set)
    for key, category in category_map.iteritems():
        category_to_keys[category].add(key)

    for category, keys in sorted(category_to_keys.items()):
        scraper_ids = sorted(set(key[0] for key in keys))
        log.info(u'{} ({})'.format(
            category, ', '.join(c for c in scraper_ids)))

        for scraper_id, scraper_category in keys:
            map_row = dict(scraper_id=scraper_id,
                           scraper_category=scraper_category,
                           category=category)

            output_row(map_row, 'scraper_category_map')


def get_company_categories(company, keys, category_map):
    category_rows = []

    for scraper_id, scraper_company in keys:
        category_rows.extend(_map_categories(
            select_company_categories(scraper_id, scraper_company),
            category_map))

    for cr_group in group_by_keys(
            category_rows, keyfunc=lambda cr: [cr['category']]):
        row = merge_dicts(cr_group)
        yield _fix_category_row(row, company)


def get_brand_categories(company, brand, keys, category_map):
    category_rows = []

    for scraper_id, scraper_company, scraper_brand in keys:

        brand_category_rows = select_brand_categories(
            scraper_id, scraper_company, scraper_brand)

        category_rows.extend(_map_categories(
            brand_category_rows, category_map))

    for cr_group in group_by_keys(
            category_rows, keyfunc=lambda cr: [cr['category']]):
        row = merge_dicts(cr_group)
        yield _fix_category_row(row, company, brand)


def _map_categories(rows, category_map):
    for row in rows:
        for k in row:
            if k == 'category' or k.endswith('_category'):
                row[k] = category_map.get((row['scraper_id'], row.get(k)))

        if not row.get('category'):  # bad category like "Other"
            continue

        yield row

def _fix_category_row(row, company=None, brand=None, category_map=None):
    del row['scraper_id']

    if company is not None:
        row['company'] = company
    if brand is not None:
        row['brand'] = brand

    return row


def output_category_hierarchy(category_map):
    cat_to_rows = defaultdict(list)
    cat_to_parents = defaultdict(set)

    # map category rows
    for cat_row in _map_categories(select_categories(), category_map):
        cat = cat_row['category']
        cat_to_rows[cat].append(cat_row)

        parent_cat = cat_row.get('parent_category')
        if parent_cat:
            cat_to_parents[cat].add(parent_cat)

    cat_to_parent = _pick_cat_parents(cat_to_parents)

    for cat, rows in sorted(cat_to_rows.items()):
        cat_row = merge_dicts(rows)
        cat_row['parent_category'] = cat_to_parent.get(cat)

        ancestry = _get_ancestry(cat, cat_to_parent)
        log.info(u' < '.join(reversed(ancestry)))

        cat_row['depth'] = len(ancestry) - 1

        for i, ancestor in enumerate(ancestry):
            cat_row['ancestor_category_{}'.format(i)] = ancestor

        output_row(cat_row, 'category')


def _pick_cat_parents(cat_to_parents):
    """Take a map from category to parents, and return a map from
    category to a single parent. Choose parents in a way that there
    are no loops."""
    cat_to_parent = {}
    cat_to_descendants = defaultdict(set)

    for cat, parents in sorted(cat_to_parents.items()):
        descendants = cat_to_descendants[cat]

        for parent in sorted(parents):
            # can end up with cats listed as their own parent due to renames
            if parent != cat and parent not in descendants:
                cat_to_parent[cat] = parent
                break

        # update descendants
        while cat in cat_to_parent:
            parent = cat_to_parent[cat]
            cat_to_descendants[parent].add(cat)
            cat_to_descendants[parent].update(cat_to_descendants[cat])
            cat = parent

    return cat_to_parent


def _get_ancestry(cat, cat_to_parent):
    ancestry = []

    while cat:
        ancestry.insert(0, cat)
        cat = cat_to_parent.get(cat)

    return ancestry
