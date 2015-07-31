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
"""Merge in extra data scraped from a url."""
from functools import lru_cache

from .table import TABLES


def match_urls(rows, scratch_db):
    """Given a list of rows, return a list of extra data (facebook_url,
    twitter_handle, etc.) scraped from the rows' web pages."""
    if isinstance(rows, dict):
        raise TypeError

    select_sql = _match_urls_select_sql()

    matches = []

    for row in rows:
        for k, maybe_url in sorted(row.items()):
            if k == 'url' and maybe_url:
                match_rows = scratch_db.execute(select_sql, [maybe_url])
                matches.extend(dict(match_row) for match_row in match_rows)

    return matches


@lru_cache()
def _match_urls_select_sql():
    cols = [c for c in TABLES['url']['columns']
            if c not in {'last_scraped', 'scraper_id', 'url'}]

    return 'SELECT {} FROM url WHERE url = ?'.format(
        ', '.join('`{}`'.format(c) for c in cols))
