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
import logging
from argparse import ArgumentParser
from os import environ

from sres.category import get_category_map
from sres.category import output_subcategory_table
from sres.category import output_scraper_category_map
from sres.company import handle_matched_company
from sres.company import match_companies
from sres.company import name_company
from sres.db import close_output_db
from sres.db import download_and_merge_dbs
from sres.db import init_output_db
from sres.db import output_row
from sres.db import select_all_campaigns
from sres.url import merge_with_url_data


log = logging.getLogger('scraper')


def main():
    opts = parse_args()

    level = logging.INFO
    if opts.verbose or environ.get('MORPH_VERBOSE'):
        level = logging.DEBUG
    elif opts.quiet:
        level = logging.WARN
    logging.basicConfig(format='%(name)s: %(message)s', level=level)

    # initialize output DB
    init_output_db()

    # create merged data
    download_and_merge_dbs(force=opts.force)

    # campaigns
    log.info('Outputting campaign table')
    for campaign_row in select_all_campaigns():
        log.info(u'campaign: {}'.format(campaign_row['campaign_id']))
        campaign_row = merge_with_url_data(campaign_row)
        output_row(campaign_row, 'campaign')

    # category map
    log.info('Outputting scraper_category_map table')
    category_map = get_category_map()
    output_scraper_category_map(category_map)

    # category, subcategory
    log.info('Outputting subcategory table')
    cat_to_ancestors = output_subcategory_table(category_map)

    # everything else
    log.info('Matching up companies')
    # handle in more-or-less alphabetical order
    cds = sorted(match_companies(), key=lambda cd: name_company(cd)[0])

    log.info('Outputting company data (all other tables)')
    for cd in cds:
        handle_matched_company(cd, category_map, cat_to_ancestors)

    close_output_db()


def parse_args(args=None):
    parser = ArgumentParser()
    parser.add_argument(
        '-v', '--verbose', dest='verbose', default=False, action='store_true',
        help='Enable debug logging')
    parser.add_argument(
        '-q', '--quiet', dest='quiet', default=False, action='store_true',
        help='Turn off info logging')
    parser.add_argument(
        '-f', '--force', dest='force', default=False, action='store_true',
        help='Force download of DBs and building of merged DB')

    return parser.parse_args(args)



if __name__ == '__main__':
    main()
