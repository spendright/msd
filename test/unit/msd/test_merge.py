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
from unittest.mock import patch

from msd.table import TABLES
from msd.merge import clean_output_row

from ...case import PatchTestCase


class TestCleanOutputRow(PatchTestCase):

    def setUp(self):
        self.start(patch.dict(TABLES,
            foo=(dict(columns=dict(foo='text'))),
            scraper_foo_map=dict(columns=dict(foo='text',
                                              scraper_id='text',
                                              scraper_foo='text')),
            bar=(dict(columns=dict(bar='text', baz='integer', foo='text'),
                      primary_key=['bar', 'baz', 'foo'])),
            qux=(dict(columns=dict(scraper_id='text',
                                   qux='text',
                                   is_quxing='tinyint',
                                   is_quuxing='tinyint',
                                   is_blanchin='tinyint'))),
        ))

    def test_empty(self):
        self.assertEqual(clean_output_row(dict(), 'foo'),
                         dict())

    def test_fills_is_fields(self):
        self.assertEqual(
            clean_output_row(dict(
                qux='x',
                is_quxing=True,
                is_quuxing=''), 'qux'),
            dict(qux='x',
                 is_quxing=1,
                 is_quuxing=0,
                 is_blanchin=0))

    def test_fills_primary_key(self):
        self.assertEqual(
            clean_output_row(dict(bar=None), 'bar'),
            dict(bar='', baz=0, foo=''))

    def test_strips_scraper_id_when_appropriate(self):
        self.assertEqual(
            clean_output_row(dict(scraper_id='ice'), 'foo'),
            dict())
        self.assertEqual(
            clean_output_row(dict(scraper_id='ice'), 'scraper_foo_map'),
            dict(scraper_id='ice'))

    def test_does_not_strip_other_fields(self):
        # we leave this to the database
        self.assertEqual(
            clean_output_row(dict(namespace='metasyntactic'), 'foo'),
            dict(namespace='metasyntactic'))
