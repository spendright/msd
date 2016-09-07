# -*- coding: utf-8 -*-
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
from unittest import TestCase

from msd.brand import build_scraper_brand_map_table
from msd.brand import pick_brand_name
from msd.brand import pick_company_for_brand
from msd.brand import split_brand_and_tm
from msd.db import insert_row

from ...db import DBTestCase
from ...db import insert_rows
from ...db import select_all


class TestSplitBrandAndTM(TestCase):

    def test_empty(self):
        self.assertEqual(split_brand_and_tm(None), ('', ''))
        self.assertEqual(split_brand_and_tm(None), ('', ''))

    def test_plain_brand(self):
        self.assertEqual(split_brand_and_tm('Panasonic'), ('Panasonic', ''))

    def test_brand_with_symbol(self):
        self.assertEqual(split_brand_and_tm('Sprite®'), ('Sprite', '®'))

    def test_discard_part_after_symbol(self):
        self.assertEqual(split_brand_and_tm('INVOKANA™ (canagliflozin) USPI'),
                         ('INVOKANA', '™'))

    def test_strip(self):
        self.assertEqual(split_brand_and_tm(' RTFM ™ '),
                         ('RTFM', '™'))

    def test_on_tm(self):
        self.assertEqual(split_brand_and_tm('™'), ('', '™'))


class TestBuildScraperBrandMapTable(DBTestCase):

    SCRATCH_TABLES = [
        'brand', 'category', 'claim', 'rating', 'scraper_brand_map']

    OUTPUT_TABLES = ['company_name', 'scraper_company_map', 'subsidiary']

    def test_merge_differing_capitalization(self):
        # this tests #19
        insert_rows(self.scratch_db, 'brand', [
            dict(brand='CardScan',
                 company='Newell Rubbermaid',
                 scraper_id='sr.campaign.hrc'),
            dict(brand='Cardscan',
                 company='Newell Rubbermaid',
                 scraper_id='sr.campaign.hrc'),
        ])

        insert_row(self.output_db, 'scraper_company_map', dict(
            company='Newell Rubbermaid',
            scraper_company='Newell Rubbermaid',
            scraper_id='sr.campaign.hrc')
        )

        build_scraper_brand_map_table(self.output_db, self.scratch_db)

        self.assertEqual(
            select_all(self.output_db, 'scraper_brand_map'),
            [dict(brand='CardScan',
                  company='Newell Rubbermaid',
                  scraper_brand='CardScan',
                  scraper_company='Newell Rubbermaid',
                  scraper_id='sr.campaign.hrc'),
             dict(brand='CardScan',
                  company='Newell Rubbermaid',
                  scraper_brand='Cardscan',
                  scraper_company='Newell Rubbermaid',
                  scraper_id='sr.campaign.hrc'),
            ])

    def test_merge_hyphens(self):
        # tests #31

        insert_rows(self.scratch_db, 'brand', [
            dict(brand='Liquid Plumr',
                 company='Clorox',
                 scraper_id='company.clorox'),
            dict(brand='Liquid-Plumr',
                 company='Clorox',
                 scraper_id='campaign.hrc'),
        ])

        insert_rows(self.output_db, 'scraper_company_map', [
            dict(company='Clorox',
                 scraper_id='company.clorox',
                 scraper_company='Clorox'),
            dict(company='Clorox',
                 scraper_id='campaign.hrc',
                 scraper_company='Clorox'),
        ])

        build_scraper_brand_map_table(self.output_db, self.scratch_db)

        self.assertEqual(
            select_all(self.output_db, 'scraper_brand_map'),
            [
                dict(brand='Liquid-Plumr',
                     company='Clorox',
                     scraper_brand='Liquid Plumr',
                     scraper_company='Clorox',
                     scraper_id='company.clorox'),
                dict(brand='Liquid-Plumr',
                     company='Clorox',
                     scraper_brand='Liquid-Plumr',
                     scraper_company='Clorox',
                     scraper_id='campaign.hrc'),
            ])

    def test_push_brand_down_to_subsidiary(self):
        # this tests #16
        insert_rows(self.scratch_db, 'brand', [
            dict(brand='Puma',
                 company='Puma',
                 scraper_id='campaign.btb_fashion'),
            dict(brand='Puma',
                 company='Kering SA',
                 scraper_id='campaign.rankabrand'),
        ])

        insert_rows(self.output_db, 'scraper_company_map', [
            dict(company='Puma',
                 scraper_company='Puma',
                 scraper_id='campaign.btb_fashion'),
            dict(company='Kering',
                 scraper_company='Kering SA',
                 scraper_id='campaign.rankabrand'),
        ])

        insert_rows(self.output_db, 'subsidiary', [
            dict(company='Kering',
                 company_depth=0,
                 subsidiary='Puma',
                 subsidiary_depth=1),
        ])

        build_scraper_brand_map_table(self.output_db, self.scratch_db)

        self.assertEqual(
            select_all(self.output_db, 'scraper_brand_map'),
            [dict(brand='Puma',
                  company='Puma',
                  scraper_brand='Puma',
                  scraper_company='Kering SA',
                  scraper_id='campaign.rankabrand'),
             dict(brand='Puma',
                  company='Puma',
                  scraper_brand='Puma',
                  scraper_company='Puma',
                  scraper_id='campaign.btb_fashion'),
            ])


class TestPickBrandName(TestCase):

    def test_empty(self):
        self.assertRaises(IndexError, pick_brand_name, [])

    def test_one(self):
        self.assertEqual(pick_brand_name(['Apple']), 'Apple')

    def test_iphone(self):
        self.assertEqual(pick_brand_name(['IPhone', 'iPhone']), 'iPhone')

    def test_all_caps(self):
        self.assertEqual(pick_brand_name(['Asus', 'ASUS']), 'Asus')

    def test_company_name_match(self):
        # tests #40
        self.assertEqual(
            pick_brand_name(['Asus', 'ASUS'], company_names={'ASUS'}),
            'ASUS')

    def test_more_caps(self):
        self.assertEqual(
            pick_brand_name(['Blackberry', 'BlackBerry']),
            'BlackBerry')


class TestPickCompanyForBrand(TestCase):

    def test_empty(self):
        self.assertRaises(IndexError, pick_company_for_brand, {}, set())

    def test_one(self):
        self.assertEqual(
            pick_company_for_brand({'Clorox': 0}, {'Liquid-Plumr'}),
            'Clorox')

    def test_match_name(self):
        self.assertEqual(
            pick_company_for_brand(
                {'Sealy': 1, 'Tempur-Pedic': 1, 'Tempur Sealy': 0},
                {'Tempur'}),
            'Tempur-Pedic')

    def test_pick_deepest_company(self):
        self.assertEqual(
            pick_company_for_brand(
                {'MEGA Brands': 1, 'Mattel': 0},
                {'Rose Art'}),
            'MEGA Brands')
