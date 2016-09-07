#   Copyright 2016 SpendRight, Inc.
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
from unittest.mock import patch

from msd.company import build_company_name_and_scraper_company_map_tables
from msd.subsidiary import build_subsidiary_table

from ...db import DBTestCase
from ...db import insert_rows
from ...db import select_all


class TestBuildSubsidiaryTable(DBTestCase):

    SCRATCH_TABLES = {
        'brand', 'category', 'claim', 'company', 'company_name',
        'rating', 'scraper_brand_map', 'scraper_company_map',
        'subsidiary'}

    def setUp(self):
        super().setUp()

    def build_tables(self):
        build_company_name_and_scraper_company_map_tables(
            self.output_db, self.scratch_db)
        build_subsidiary_table(self.output_db, self.scratch_db)

    def test_empty(self):
        self.build_tables()

        rows = select_all(self.output_db, 'subsidiary')
        self.assertEqual(rows, [])

    def test_parent_company(self):
        insert_rows(self.scratch_db, 'subsidiary', [
            dict(
                company='Campbell Soup',
                scraper_id='s',
                subsidiary='Plum Organics',
            ),
        ])

        self.build_tables()

        rows = select_all(self.output_db, 'subsidiary')
        self.assertEqual(rows, [
            dict(
                company='Campbell Soup',
                company_depth=0,
                subsidiary='Plum Organics',
                subsidiary_depth=1,
            ),
        ])

    def test_multilevel_subsidiary(self):
        insert_rows(self.scratch_db, 'subsidiary', [
            dict(
                company='VF',
                scraper_id='s',
                subsidiary='VF Outdoor',
            ),
            dict(
                company='VF Outdoor',
                scraper_id='s',
                subsidiary='Vans',
            ),
        ])

        self.build_tables()

        rows = select_all(self.output_db, 'subsidiary')
        self.assertEqual(rows, [
            dict(
                company='VF',
                company_depth=0,
                subsidiary='VF Outdoor',
                subsidiary_depth=1,
            ),
            dict(
                company='VF',
                company_depth=0,
                subsidiary='Vans',
                subsidiary_depth=2,
            ),
            dict(
                company='VF Outdoor',
                company_depth=1,
                subsidiary='Vans',
                subsidiary_depth=2,
            ),
        ])

    def test_pick_longest_ancestor_path(self):
        insert_rows(self.scratch_db, 'subsidiary', [
            dict(
                company='VF',
                scraper_id='s',
                subsidiary='Vans',
            ),
        ])

        self.test_multilevel_subsidiary()

    def test_break_cycle(self):
        insert_rows(self.scratch_db, 'subsidiary', [
            dict(
                company='AAA',
                scraper_id='s',
                subsidiary='BBB',
            ),
            dict(
                company='BBB',
                scraper_id='s',
                subsidiary='AAA',
            )
        ])

        with patch('msd.subsidiary.log') as mock_log:
            self.build_tables()

            self.assertTrue(mock_log.warning.called)

        # we resolve companies in sorted order
        rows = select_all(self.output_db, 'subsidiary')
        self.assertEqual(rows, [
            dict(
                company='BBB',
                company_depth=0,
                subsidiary='AAA',
                subsidiary_depth=1,
            ),
        ])

    def test_ignore_bad_entries(self):
        insert_rows(self.scratch_db, 'subsidiary', [
            dict(
                company='VF',
                scraper_id='s',
            ),
            dict(
                scraper_id='s',
                subsidiary='Vans',
            ),
        ])

        self.build_tables()

        rows = select_all(self.output_db, 'subsidiary')
        self.assertEqual(rows, [])
