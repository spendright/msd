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
from .db import select_brand_categories
from .db import select_categories
from .db import select_company_categories
from .db import select_subcategories
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


def output_category_and_subcategory_tables(category_map):
    cat_to_rows = defaultdict(list)
    cat_to_children = defaultdict(set)
    # tuples of parent_category, category
    direct_subcategories = set()

    # read category table
    for row in _map_categories(select_categories(), category_map):
        cat = row['category']
        cat_to_rows[cat].append(row)

        if row.get('parent_category'):
            parent_cat = row['parent_category']

            cat_to_children[parent_cat].add(cat)
            direct_subcategories.add((parent_cat, cat))

    # read subcategory table
    for row in _map_categories(select_subcategories(), category_map):
        cat = row['category']
        subcat = row['subcategory']

        cat_to_children[cat] = subcat
        if not row.get('is_implied'):
            direct_subcategories.add((cat, subcat))

    # output category table
    for cat, rows in sorted(cat_to_rows.items()):
        row = merge_dicts(rows)
        # parent_category has been replaced by subcategory table
        row.pop('parent_category', None)

        output_row(row, 'category')

    # output subcategory table
    cat_to_ancestors = _imply_category_ancestors(cat_to_children)

    for cat, ancestors in cat_to_ancestors.iteritems():
        for ancestor in ancestors:
            subcat_row = {'category': ancestor, 'subcategory': cat}
            if (ancestor, cat) not in direct_subcategories:
                subcat_row['is_implied'] = 1

            output_row(subcat_row, 'subcategory')

    # needed later
    return cat_to_ancestors


def _imply_category_ancestors(cat_to_children):
    cat_to_ancestors = defaultdict(set)
    active_cats = set(cat_to_children)

    while active_cats:
        next_active_cats = set()

        for active_cat in active_cats:
            children = cat_to_children.get(active_cat, ())
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

def _fix_category_row(row, company=None, brand=None, category_map=None):
    del row['scraper_id']

    if company is not None:
        row['company'] = company
    if brand is not None:
        row['brand'] = brand

    return row


def get_implied_categories(cats, cat_to_ancestors):
    cats = set(cats)

    implied_cats = set()
    for cat in cats:
        implied_cats.update(cat_to_ancestors.get(cat) or ())

    implied_cats -= cats
    return implied_cats
