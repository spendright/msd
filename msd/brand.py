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

from .merge import create_output_table

log = getLogger(__name__)


def build_brand_table(output_db, scratch_db):
    log.info('  building brand table')
    create_output_table(output_db, 'brand')
    log.warning('    NOT YET IMPLEMENTED')


def build_scraper_brand_map_table(output_db, scratch_db):
    log.info('  building scraper_brand_map table')
    create_output_table(output_db, 'scraper_brand_map')
    log.warning('    NOT YET IMPLEMENTED')
