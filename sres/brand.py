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
"""Utilities for merging brand information."""
import logging

from srs.norm import smunch

from .db import select_brands
from .norm import fix_bad_chars
from .norm import group_by_keys
from .url import merge_with_url_data


BRAND_CORRECTIONS = {
    # this is actually the name of a subsidary
    'Taylormade - Adidas Golf': 'TaylorMade',
    'Wendys': "Wendy's",
    '7 Up': '7UP',
}

# incorrect brand information for particular scrapers
# this maps scraper_id to company name used by that scraper
IGNORE_BRANDS = {
    'campaigns:climate_counts': {
        'Baxter International': None,
        'Britax': None,
        'Clorox': None,
        'Coca-Cola Company': None,
        'ConAgra Foods': None,
        'ExpressJet': None,
        'General Electric': None,
        'General Mills': None,
        'Groupe Danone': {'LU'},  # sold in 2007
        'Hillshire': None,
        'Kraft Foods': None,
        'Liz Claiborne': None,  # sold most brands, now Kate Spade & Company
        'News Corporation': None,  # recently split
        'Sony': None,
        "Wendy's": None,  # used to be part of a conglomerate, now just Wendy's
        'eBay': {'GE'},  # ???
    },
    'campaigns:free2work': {
        'Bob Barker Company': {  # makes prison supplies
            'Comfort Zone',
            'Liberty',  # heh
            'MacGregor',
            'Tristich'
        },
        'Hanesbrands Incorporated': None,  # use company scraper
    },
}


log = logging.getLogger(__name__)


def fix_brand(brand):
    brand = BRAND_CORRECTIONS.get(brand) or brand
    brand = fix_bad_chars(brand)

    return brand


def get_brands_for_company(keys):
    """Given keys, a list of (scraper_id, company), return a dictionary
    mapping canonical brand name to information about that brand."""

    # we'll eventually need the ability to choose a master list
    # of brands (so we can ignore brands that a campaign wrongly
    # assigns to a company), and be able to handle variant spellings
    # (e.g. Liquid-Plumr/LiquidPlumr)

    # We'll also need to catch when a brand has been rated but isn't
    # in the master list (include it but issue a warning)
    brand_rows = []
    for scraper_id, company in sorted(keys):
        if (scraper_id in IGNORE_BRANDS and
            company in IGNORE_BRANDS[scraper_id]):

            if IGNORE_BRANDS[scraper_id][company] is None:
                continue  # None means exclude all brands
            else:
                ignore = IGNORE_BRANDS[scraper_id][company]
        else:
            ignore = ()

        for brand_row in select_brands(scraper_id, company):
            if brand_row['brand'] not in ignore:
                brand_row['brand'] = fix_brand(brand_row['brand'])
                brand_rows.append(brand_row)

    def keyfunc(brand_row):
        return smunch(brand_row['brand'])

    brand_to_row = {}
    brand_map = {}

    for brand_row_group in group_by_keys(brand_rows, keyfunc):
        # don't give special priority to brands from company scrapers;
        # these are sometimes ALL CAPS
        #
        # TODO: revisit this. If a brand from a company scraper *isn't*
        # all caps, it's more likely to be the correct spelling than
        # data from a campaign.
        brand = pick_brand_name(br['brand'] for br in brand_row_group)

        # update mapping
        for br in brand_row_group:
            brand_map[(br['scraper_id'], br['brand'])] = brand

        brand_row = merge_with_url_data(brand_row_group)
        brand_row['brand'] = brand
        del brand_row['scraper_id']

        brand_to_row[brand] = brand_row

    return brand_to_row, brand_map


def pick_brand_name(variants):
    """Given several versions of a brand name, prefer the one
    that is not all-lowercase, not all-uppercase, longest,
    and starts with a lowercase letter ("iPhone" > "IPhone"),
    and has the most capital letters ("BlackBerry" > "Blackberry").
    """
    def keyfunc(v):
        return (v != v.lower(),
                v != v.upper(),
                len(v),
                v[0],
                sum(1 for c in v if c.upper() == c))

    return sorted(variants, key=keyfunc, reverse=True)[0]
