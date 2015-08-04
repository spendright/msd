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
"""Entry point for building the output table.

To avoid circular dependencies, most of the supporting code to build the
output table is in merge.py
"""
from logging import getLogger
from os import remove
from os import rename
from os.path import exists

from .brand import build_brand_table
from .brand import build_scraper_brand_map_table
from .campaign import build_campaign_table
from .category import build_category_table
from .category import build_scraper_category_map_table
from .category import build_subcategory_table
from .claim import build_claim_table
from .company import build_company_table
from .company import build_company_name_and_scraper_company_map_tables
from .rating import build_rating_table
from .scraper import build_scraper_table

from .db import open_db

log = getLogger(__name__)


def build_output_db(scratch_db_path, output_db_path):
    output_db_tmp_path = output_db_path + '.tmp'

    log.info('building {}...'.format(output_db_tmp_path))

    if exists(output_db_tmp_path):
        remove(output_db_tmp_path)

    with open_db(output_db_tmp_path) as output_db:
        with open_db(scratch_db_path) as scratch_db:
            fill_output_db(output_db, scratch_db)

    log.info('moving {} -> {}'.format(output_db_tmp_path, output_db_path))
    rename(output_db_tmp_path, output_db_path)


def fill_output_db(output_db, scratch_db):
    # tables with no dependencies
    build_campaign_table(output_db, scratch_db)
    build_scraper_table(output_db, scratch_db)

    # category names
    build_scraper_category_map_table(output_db, scratch_db)
    build_subcategory_table(output_db, scratch_db)

    # companies
    build_company_name_and_scraper_company_map_tables(output_db, scratch_db)
    build_company_table(output_db, scratch_db)

    # TODO: subsidiaries would be handled here

    # brands
    build_scraper_brand_map_table(output_db, scratch_db)
    build_brand_table(output_db, scratch_db)

    # things that key on company, brand
    build_category_table(output_db, scratch_db)
    build_claim_table(output_db, scratch_db)
    build_rating_table(output_db, scratch_db)
