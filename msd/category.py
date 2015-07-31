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
from logging import getLogger

from msd.merge import create_output_table

log = getLogger(__name__)


def build_category_table(output_db, scratch_db):
    log.info('  building category table')
    create_output_table(output_db, 'category')
    log.warning('  filling category table not yet implemented')


def build_scraper_category_map_table(output_db, scratch_db):
    log.info('  building scraper_category_map table')
    create_output_table(output_db, 'scraper_category_map')
    log.warning('  filling scraper_category_map table not yet implemented')


def build_subcategory_table(output_db, scratch_db):
    log.info('  building subcategory table')
    create_output_table(output_db, 'subcategory')
    log.warning('  filling subcategory table not yet implemented')
