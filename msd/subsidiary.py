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
from collections import defaultdict
from logging import getLogger

from .company import map_company
from .merge import create_output_table
from .merge import output_row

log = getLogger(__name__)


def build_subsidiary_table(output_db, scratch_db):
    log.info('  building subsidiary table')
    create_output_table(output_db, 'subsidiary')

    # read in subsidiary info
    company_to_parents = defaultdict(set)

    select_sql = (
        'SELECT scraper_id, company, subsidiary from subsidiary')

    for scraper_id, scraper_company, scraper_subsidiary in (
            scratch_db.execute(select_sql)):

        company = map_company(output_db, scraper_id, scraper_company)
        subsidiary = map_company(output_db, scraper_id, scraper_subsidiary)

        if not (company and subsidiary):
            continue

        company_to_parents[subsidiary].add(company)

    # pick the longest possible ancestry for each company

    company_to_ancestry = {}

    def pick_ancestry(company, not_parents):
        # already picked
        if company in company_to_ancestry:
            return company_to_ancestry[company]

        parents = company_to_parents[company]

        # cycles shouldn't happen; just don't loop forever
        if parents & not_parents:
            log.warning(
                'cyclical subsidiary relationship for {}'.format(company))
            parents = parents - not_parents

        if len(parents) == 0:
            ancestry = []
        else:
            # recurse, using the longest
            ancestry = longest(
                [parent] + pick_ancestry(parent, not_parents=(
                    not_parents | {company}))
                for parent in parents)

        company_to_ancestry[company] = ancestry
        return ancestry

    def longest(ancestries):
        return sorted(ancestries, key=lambda a: (-len(a), a))[0]

    for company in sorted(company_to_parents):
        pick_ancestry(company, set())

    # output rows

    for company, ancestry in sorted(company_to_ancestry.items()):
        for depth, ancestor in enumerate(reversed(ancestry)):
            output_row(output_db, 'subsidiary', dict(
                company=ancestor,
                company_depth=depth,
                subsidiary=company,
                subsidiary_depth=len(ancestry),
            ))
