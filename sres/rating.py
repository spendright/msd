# -*- coding: utf-8 -*-

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
from collections import defaultdict
from logging import getLogger

from .norm import merge_dicts


# these fields form a unique key
KEY_FIELDS = ['campaign_id', 'company', 'brand', 'scope']

# these should match when two ratings are the same
NON_MATCHING_FIELDS = ['url']

log = getLogger(__name__)


def merge_ratings(rating_rows):
    """Merge ratings, raising an exception if there's a conflict."""
    rating_key_to_rows = defaultdict(list)

    for row in rating_rows:
        rating_key = tuple(row.get(k) for k in KEY_FIELDS)
        rating_key_to_rows[rating_key].append(row)

    for rating_key, rows in sorted(rating_key_to_rows.iteritems()):
        key_to_values = defaultdict(set)

        for row in rows:
            for k, v in row.iteritems():
                key_to_values[k].add(v)

        conflicts = sorted(k for k, vs in key_to_values.iteritems()
                           if len(vs) > 1 and k not in NON_MATCHING_FIELDS)
        if conflicts:
            log.warn('ratings conflict on {}: {}'.format(
                ', '.join(conflicts), repr(rows)))

        yield merge_dicts(rows)
