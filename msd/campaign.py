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

from .db import select_groups
from .merge import create_output_table
from .merge import merge_dicts
from .merge import output_row
from .url import match_urls

log = getLogger(__name__)


def build_campaign_table(output_db, scratch_db):
    log.info('  building campaign table')
    create_output_table(output_db, 'campaign')

    for (campaign_id,), rows in select_groups(
            scratch_db, 'campaign', ['campaign_id']):

        if not campaign_id:
            continue

        campaign_row = merge_dicts(rows + match_urls(rows, scratch_db))
        output_row(output_db, 'campaign', campaign_row)
