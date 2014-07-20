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
"""Utilities for merging brand information."""
from .db import select_campaign_brands
from .norm import group_by_keys
from .norm import merge_dicts
from .norm import norm_with_variants


def get_brands_for_company(keys):
    """Given keys, a list of (campaign_id, company), return a dictionary
    mapping canonical brand name to information about that brand."""

    # we'll eventually need the ability to choose a master list
    # of brands (so we can ignore brands that a campaign wrongly
    # assigns to a company), and be able to handle variant spellings
    # (e.g. Liquid-Plumr/LiquidPlumr)

    # We'll also need to catch when a brand has been rated but isn't
    # in the master list (include it but issue a warning)
    brand_rows = []
    for campaign_id, company in sorted(keys):
        brand_rows.extend(select_campaign_brands(campaign_id, company))

    def keyfunc(brand_row):
        return norm_with_variants(brand_row['brand'])

    brand_to_row = {}
    brand_map = {}

    for brand_row_group in group_by_keys(brand_rows, keyfunc):
        # pick the version of the brand that is not all one case
        # and is longest
        brand = pick_brand_name(br['brand'] for br in brand_row_group)

        # update mapping
        for br in brand_row_group:
            brand_map[(br['campaign_id'], br['brand'])] = brand

        brand_row = merge_dicts(brand_row_group)
        brand_row['brand'] = brand
        del brand_row['campaign_id']

        brand_to_row[brand] = brand_row

    return brand_to_row, brand_map


def pick_brand_name(variants):
    """Given several versions of a brand name, prefer the one
    that is not all-lowercase, not all-uppercase, longest,
    and starts with a lowercase letter ("iPhone" > "IPhone")."""
    return sorted(variants,
        key=lambda v: (v != v.lower(), v != v.upper(), len(v), v),
        reverse=True)[0]
