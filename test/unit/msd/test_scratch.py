# -*- coding: utf-8 -*-
# Copyright 2016 SpendRight, Inc.
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

from msd.scratch import parse_input_path


class TestParseInputPath(TestCase):

    def test_empty(self):
        self.assertRaises(ValueError, parse_input_path, '')

    def test_sqlite(self):
        self.assertEqual(parse_input_path('sr.company.sqlite'),
                         ('sr.company', 'sqlite'))

    def test_yaml(self):
        self.assertEqual(parse_input_path('manual/detox_catwalk.yaml'),
                         ('manual/detox_catwalk', 'yaml'))

    def test_other_format(self):
        self.assertRaises(ValueError, parse_input_path, 'README.txt')

    def test_uppercase_format(self):
        self.assertEqual(parse_input_path('DATA.YAML'),
                         ('DATA', 'yaml'))
