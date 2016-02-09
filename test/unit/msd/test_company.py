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
from unittest import TestCase

from msd.company import build_company_name_and_scraper_company_map_tables
from msd.company import get_company_aliases
from msd.company import get_company_names

from ...db import DBTestCase
from ...db import insert_rows
from ...db import select_all


class TestGetCompanyNames(TestCase):

    def test_empty(self):
        self.assertEqual(get_company_names(''), set())

    def test_too_short(self):
        self.assertEqual(get_company_names('Y'), set())

    def test_variant_too_short(self):
        self.assertEqual(get_company_names('L Brands'), {'L Brands'})

    def test_weird_caching_bug(self):
        # for some reason, would get {'L', 'L Brands'} after calling
        # get_company_aliases()
        get_company_aliases('L Brands')
        self.assertEqual(get_company_names('L Brands'), {'L Brands'})

    def test_basic(self):
        self.assertEqual(get_company_names('Konica'), {'Konica'})

    def test_lowercase_a_s(self):
        # this tests #30
        self.assertEqual(get_company_names('bisgaard sko a/s'),
                         {'bisgaard sko a/s', 'bisgaard sko'})

    def test_pvt_ltd(self):
        # this tests #12
        self.assertEqual(get_company_names('Servals Pvt Ltd'),
                         {'Servals', 'Servals Pvt Ltd'})


class TestBuildCompanyNameAndScraperCompanyMapTables(DBTestCase):

    # need everything with a "company" column in it
    SCRATCH_TABLES = {
        'brand', 'category', 'claim', 'company', 'company_name',
        'rating', 'scraper_brand_map', 'scraper_company_map'}

    def test_dont_merge_l_international_and_l_brands(self):
        # this tests #33
        insert_rows(self.scratch_db, 'company', [
            dict(company='L. International',
                 scraper_id='sr.campaign.b_corp'),
            dict(company='L Brands',
                 scraper_id='sr.campaign.hrc'),
        ])

        build_company_name_and_scraper_company_map_tables(
            self.output_db, self.scratch_db)

        rows = select_all(self.output_db, 'scraper_company_map')
        companies = {row['company'] for row in rows}

        self.assertEqual(len(rows), 2)
        self.assertIn('L.', companies)

    def test_no_single_letter_company_names(self):

        insert_rows(self.scratch_db, 'company', [
            dict(company='L Brands',
                 scraper_id='sr.campaign.hrc'),
        ])

        build_company_name_and_scraper_company_map_tables(
            self.output_db, self.scratch_db)

        rows = select_all(self.output_db, 'scraper_company_map')
        companies = {row['company'] for row in rows}

        self.assertEqual(companies, {'L Brands'})
