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
from .target import select_groups_by_target

log = getLogger(__name__)


def build_rating_table(output_db, scratch_db):
    log.info('  building rating table')
    create_output_table(output_db, 'rating')

    def keyfunc(row):
        return row['campaign_id']

    # slice by target
    for (company, brand), campaign_id, rating_rows in \
        select_groups_by_target(
            output_db, scratch_db, 'rating', ['campaign_id']):

        if not (campaign_id):
            continue

        rating_row = merge_dicts(rating_rows)

        rating_row['company'] = company
        rating_row['brand'] = brand
        if rating_row['grade']:
            rating_row['grade'] = str(rating_row['grade']).upper()

        rating_row['judgment'] = fix_judgment(rating_row['judgment'])

        if rating_row['judgment'] is None and rating_row['grade']:
            rating_row['judgment'] = grade_to_judgment(rating_row['grade'])

        if rating_row['judgment'] is None:
            continue

        # fill min_score
        if (rating_row.get('score') is not None and
            rating_row.get('min_score') is None):

            rating_row['min_score'] = 0

        output_row(output_db, 'rating', rating_row)


def fix_judgment(judgment):
    """Make sure judgment is -1, 0, 1, or None."""
    try:
        judgment = float(judgment)
    except TypeError:
        return None

    if judgment > 0:
        return 1
    elif judgment < 0:
        return -1
    else:
        return 0


def grade_to_judgment(grade):
    letter = grade[:1]

    if letter in 'AB':
        return 1
    elif letter == 'C':
        return 0
    elif letter in 'DEF':
        return -1
    else:
        return None
