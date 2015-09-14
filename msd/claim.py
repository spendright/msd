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
from .merge import merge_dicts
from .merge import output_row
from .rating import fix_judgment
from .target import select_groups_by_target

log = getLogger(__name__)


def build_claim_table(output_db, scratch_db):
    log.info('  building claim table')
    create_output_table(output_db, 'claim')

    # slice by target
    for (company, brand), (campaign_id, claim), claim_rows in \
        select_groups_by_target(
            output_db, scratch_db, 'claim', ['campaign_id', 'claim']):

        if not (campaign_id and claim):
            continue

        claim_row = merge_dicts(claim_rows)
        claim_row['company'] = company
        claim_row['brand'] = brand
        claim_row['judgment'] = fix_judgment(claim_row['judgment'])

        if claim_row['judgment'] is None:
            continue

        output_row(output_db, 'claim', claim_row)
