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

from msd.company import get_company_variants


class TestVariants(TestCase):

    def test_empty(self):
        self.assertEqual(get_company_variants(''), set())

    def test_too_short(self):
        self.assertEqual(get_company_variants('Y'), set())

    def test_basic(self):
        self.assertEqual(get_company_variants('Konica'), {'Konica'})
