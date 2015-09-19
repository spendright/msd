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
from msd.db import select_groups

from ...db import DBTestCase
from ...db import insert_rows
from ...db import sorted_rows


class TestSelectGroups(DBTestCase):

    OUTPUT_TABLES = ['scraper_company_map']

    def test_empty(self):
        self.assertEqual(
            list(select_groups(
                self.output_db, 'scraper_company_map', ['company'])),
            [])

    def test_one_row_group(self):
        ONE_ROW = dict(
            company='Foo',
            scraper_company='Foo',
            scraper_id='sr.campaign.bar')

        insert_row(self.output_db, 'scraper_company_map', ONE_ROW)

        self.assertEqual(
            list(select_groups(
                self.output_db, 'scraper_company_map', ['company'])),
            [(('Foo',), [ONE_ROW])])

    def test_two_row_group(self):
        TWO_ROWS = [
            dict(company='Foo',
                 scraper_company='Foo',
                 scraper_id='sr.campaign.bar'),
            dict(company='Foo',
                 scraper_company='Foo & Co.',
                 scraper_id='sr.campaign.qux'),
        ]

        insert_rows(self.output_db, 'scraper_company_map', TWO_ROWS)

        groups = [(key, sorted_rows(rows))
                  for key, rows in select_groups(
                          self.output_db, 'scraper_company_map', ['company'])]

        self.assertEqual(groups,
                         [(('Foo',), TWO_ROWS)])
