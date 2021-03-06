#   Copyright 2014-2016 SpendRight, Inc.
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
from msd.company import pick_company_full
from msd.company import pick_company_name

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
        # would get {'L', 'L Brands'} after calling
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

    def test_turkish_a_s(self):
        # this tests #45
        self.assertEqual(get_company_names('Arçelik A.Ş'),
                         {'Arçelik', 'Arçelik A.Ş'})

    def test_comma_llc(self):
        # this tests #35
        self.assertEqual(get_company_names('Indosole, LLC'),
                         {'Indosole', 'Indosole, LLC'})

    def test_x_dot_com(self):
        self.assertEqual(get_company_names('Zappos.com'),
                         {'Zappos.com'})


class TestGetCompanyAliases(TestCase):

    def test_x_com(self):
        # this tests #52
        self.assertEqual(get_company_aliases('Zappos.com'),
                         {'Zappos.com', 'Zappos'})


class TestPickCompanyName(TestCase):

    def test_empty(self):
        self.assertRaises(IndexError, pick_company_name, [])

    def test_one(self):
        self.assertEqual(pick_company_name(['Singularity']), 'Singularity')

    def test_shortest(self):
        self.assertEqual(
            pick_company_name(['The Coca-Cola Company', 'Coca-Cola']),
            'Coca-Cola')

    def test_all_caps(self):
        self.assertEqual(
            pick_company_name(['ASUS', 'Asus']),
            'ASUS')

    def test_all_lowercase(self):
        self.assertEqual(
            pick_company_name(['Illy', 'illy']),
            'Illy')


class TestPickCompanyFull(TestCase):

    def test_empty(self):
        self.assertRaises(IndexError, pick_company_full, [])

    def test_one(self):
        self.assertEqual(pick_company_full(['Singularity']), 'Singularity')

    def test_longest(self):
        self.assertEqual(
            pick_company_full(['The Coca-Cola Company', 'Coca-Cola']),
            'The Coca-Cola Company')

    def test_all_caps(self):
        self.assertEqual(
            pick_company_full(['ASUS', 'Asus']),
            'ASUS')

    def test_all_lowercase(self):
        self.assertEqual(
            pick_company_full(['Illy', 'illy']),
            'Illy')


class TestBuildCompanyNameAndScraperCompanyMapTables(DBTestCase):

    # need everything with a "company" column in it
    SCRATCH_TABLES = {
        'brand', 'category', 'claim', 'company', 'company_name',
        'rating', 'scraper_brand_map', 'scraper_company_map',
        'subsidiary'}

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

    def test_merge_pvh_and_pvh_corp(self):
        # regression test for separate PVH, PVH Corp.
        insert_rows(self.scratch_db, 'company', [
            dict(company='PVH',
                 scraper_id='campaign.hrc'),
            dict(company='PVH Corp',
                 scraper_id='campaign.btb_fashion'),
        ])

        build_company_name_and_scraper_company_map_tables(
        self.output_db, self.scratch_db)

        # verify that companies merged
        map_rows = select_all(self.output_db, 'scraper_company_map')
        self.assertEqual(len(map_rows), 2)
        self.assertEqual(set(row['company'] for row in map_rows), {'PVH'})

        name_rows = select_all(self.output_db, 'scraper_company_map')
        self.assertEqual(len(map_rows), 2)
        for row in name_rows:
            if row.get('is_full'):
                # add trailing period
                self.assertEqual(row['company_name'], 'PVH Corp.')

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

    def test_news_corporation(self):
        # mark company name as invariant
        insert_rows(self.scratch_db, 'company_name', [
            dict(company_name='News Corporation',
                 scraper_id='corrections.company_name'),
        ])

        insert_rows(self.scratch_db, 'company', [
            dict(company='News Corporation',
                 scraper_id='campaign.climate_counts'),
        ])

        build_company_name_and_scraper_company_map_tables(
            self.output_db, self.scratch_db)

        rows = select_all(self.output_db, 'scraper_company_map')
        companies = {row['company'] for row in rows}

        self.assertEqual(companies, {'News Corporation'})

    def test_asus(self):
        # make sure company_name from company_name table is used
        insert_rows(self.scratch_db, 'company_name', [
            dict(company='ASUS',
                 company_name='ASUSTek Computer Inc.',
                 is_full=1,
                 scraper_id='corrections/company_name')
        ])

        build_company_name_and_scraper_company_map_tables(
            self.output_db, self.scratch_db)

        map_rows = select_all(self.output_db, 'scraper_company_map')
        companies = {row['company'] for row in map_rows}
        self.assertEqual(companies, {'ASUS'})

        name_rows = select_all(self.output_db, 'company_name')
        company_fulls = {row['company_name'] for row in name_rows
                         if row['is_full']}
        self.assertEqual(company_fulls, {'ASUSTek Computer Inc.'})

    def test_the_limited(self):
        # "The Limited" is a very old name for L Brands
        insert_rows(self.scratch_db, 'company_name', [
            dict(company_name='The Limited',
                 scraper_id='corrections/company_name'),
            dict(company='L Brands',
                 company_name='The Limited',
                 is_alias=1,
                 scraper_id='corrections/company_name'),
        ])

        insert_rows(self.scratch_db, 'rating', [
            dict(campaign_id='hsus_fur_free',
                 company='The Limited',
                 judgment=1,
                 scraper_id='campaign/hsus_fur_free'),
        ])

        build_company_name_and_scraper_company_map_tables(
            self.output_db, self.scratch_db)

        company_map = {
            (row['scraper_id'], row['scraper_company']): row['company']
            for row in select_all(self.output_db, 'scraper_company_map')
        }
        self.assertEqual(
            company_map.get(('campaign/hsus_fur_free', 'The Limited')),
            'L Brands')
