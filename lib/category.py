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
"""Utilities for category information."""
import logging
from collections import defaultdict

from titlecase import titlecase

from .db import output_row
from .db import select_all_categories
from .db import select_brand_categories
from .db import select_company_categories
from .norm import fix_bad_chars
from .norm import group_by_keys
from .norm import merge_dicts
from .norm import simplify_whitespace


BAD_CATEGORIES = {
    'Commercial Products',
    'Industry Innovators',
    'Other',
}

log = logging.getLogger(__name__)


def fix_category(category, campaign_id):
    category = fix_bad_chars(category)
    category = category.replace('&', ' and ')
    category = simplify_whitespace(category)
    category = titlecase(category)

    if category.endswith(' Brands'):
        category = category[:-7]

    if not category or category in BAD_CATEGORIES:
        return None
    else:
        return category


def get_category_map():
    key_to_category = {}

    for campaign_id, campaign_category in select_all_categories():
        category = fix_category(campaign_category, campaign_id)
        if category is None:
            continue

        key_to_category[(campaign_id, campaign_category)] = category

    return key_to_category


def output_category_rows(category_map):
    category_to_keys = defaultdict(set)
    for key, category in category_map.iteritems():
        category_to_keys[category].add(key)

    for category, keys in sorted(category_to_keys.items()):
        campaign_ids = sorted(set(key[0] for key in keys))
        log.info(u'{} ({})'.format(
            category, ', '.join(c for c in campaign_ids)))

        for campaign_id, campaign_category in keys:
            map_row = dict(campaign_id=campaign_id,
                           campaign_category=campaign_category,
                           category=category)

            output_row(map_row, 'campaign_category_map')


def get_company_categories(company, keys, category_map):
    category_rows = []

    for campaign_id, campaign_company in keys:
        category_rows.extend(_map_categories(
            select_company_categories(campaign_id, campaign_company),
            campaign_id, category_map))

    for cr_group in group_by_keys(
            category_rows, keyfunc=lambda cr: [cr['category']]):
        row = merge_dicts(cr_group)
        yield _fix_category_row(row, company)


def get_brand_categories(company, brand, keys, category_map):
    category_rows = []

    for campaign_id, campaign_company, campaign_brand in keys:

        brand_category_rows = select_brand_categories(
            campaign_id, campaign_company, campaign_brand)

        category_rows.extend(_map_categories(
            brand_category_rows, campaign_id, category_map))

    for cr_group in group_by_keys(
            category_rows, keyfunc=lambda cr: [cr['category']]):
        row = merge_dicts(cr_group)
        yield _fix_category_row(row, company, brand)


def _map_categories(rows, campaign_id, category_map):
    for row in rows:
        category = category_map.get((campaign_id, row['category']))
        if not category:  # bad category like "Other"
            continue
        row['category'] = category

        yield row

def _fix_category_row(row, company, brand=None):
    del row['campaign_id']

    row['company'] = company
    if brand is not None:
        row['brand'] = brand

    return row
