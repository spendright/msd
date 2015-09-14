# -*- coding: utf-8 -*-
# Copyright 2015 SpendRight, Inc.
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
from msd.db import insert_row
from msd.claim import build_claim_table

from ...db import DBTestCase
from ...db import select_all
from ...db import strip_null


class TestBuildClaimTable(DBTestCase):

    SCRATCH_TABLES = ['claim']

    OUTPUT_TABLES = ['scraper_brand_map', 'scraper_company_map']

    def setUp(self):
        super().setUp()

        # have company/brand maps ready
        insert_row(self.output_db, 'scraper_company_map', dict(
            scraper_id='sr.campaign.qux',
            company='Foo',
            scraper_company='Foo & Co.'))

        insert_row(self.output_db, 'scraper_brand_map', dict(
            scraper_id='sr.campaign.qux',
            company='Foo',
            brand='Bar',
            scraper_company='Foo & Co.',
            scraper_brand='BAR™'))

    def test_map_company(self):
        insert_row(self.scratch_db, 'claim', dict(
            scraper_id='sr.campaign.qux',
            campaign_id='qux',
            company='Foo & Co.',
            brand='',
            claim='>80% of variables are metasyntactic',
            judgment=1))

        build_claim_table(self.output_db, self.scratch_db)

        self.assertEqual(
            [strip_null(row) for row in select_all(self.output_db, 'claim')],
            [dict(campaign_id='qux',
                  company='Foo',
                  brand='',
                  scope='',
                  claim='>80% of variables are metasyntactic',
                  judgment=1)])

    def test_map_brand(self):
        insert_row(self.scratch_db, 'claim', dict(
            scraper_id='sr.campaign.qux',
            campaign_id='qux',
            company='Foo & Co.',
            brand='BAR™',
            claim='code of conduct mandates unreadable code',
            judgment=-1))

        build_claim_table(self.output_db, self.scratch_db)

        self.assertEqual(
            [strip_null(row) for row in select_all(self.output_db, 'claim')],
            [dict(campaign_id='qux',
                  company='Foo',
                  brand='Bar',
                  scope='',
                  claim='code of conduct mandates unreadable code',
                  judgment=-1)])

    def test_discard_null_judgment(self):
        # this tests issue #22
        insert_row(self.scratch_db, 'claim', dict(
            scraper_id='sr.campaign.qux',
            campaign_id='qux',
            company='Foo & Co.',
            brand='',
            claim='>80% of variables are metasyntactic'))

        build_claim_table(self.output_db, self.scratch_db)

        self.assertEqual(select_all(self.output_db, 'claim'), [])
