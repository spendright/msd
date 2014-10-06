import logging
from argparse import ArgumentParser
from os import environ

from lib.category import get_category_map
from lib.category import output_category_rows
from lib.company import match_companies
from lib.company import name_company
from lib.company import handle_matched_company
from lib.db import output_row
from lib.db import close_output_db
from lib.db import download_and_merge_dbs
from lib.db import select_all_campaigns


log = logging.getLogger('scraper')


def main():
    opts = parse_args()

    level = logging.INFO
    if opts.verbose or environ.get('MORPH_VERBOSE'):
        level = logging.DEBUG
    elif opts.quiet:
        level = logging.WARN
    logging.basicConfig(format='%(name)s: %(message)s', level=level)

    # create merged data
    download_and_merge_dbs()

    return

    # campaigns
    log.info('Outputting campaign table')
    for campaign_row in select_all_campaigns():
        log.info(u'campaign: {}'.format(campaign_row['campaign_id']))
        output_row(campaign_row, 'campaign')

    # category map
    log.info('Outputting category_map table')
    category_map = get_category_map()
    output_category_rows(category_map)

    # everything else
    log.info('Matching up companies')
    # handle in more-or-less alphabetical order
    cds = sorted(match_companies(), key=lambda cd: name_company(cd)[0])

    log.info('Outputting company data (all other tables)')
    for cd in cds:
        handle_matched_company(cd, category_map)

    close_output_db()


def parse_args(args=None):
    parser = ArgumentParser()
    parser.add_argument(
        '-v', '--verbose', dest='verbose', default=False, action='store_true',
        help='Enable debug logging')
    parser.add_argument(
        '-q', '--quiet', dest='quiet', default=False, action='store_true',
        help='Turn off info logging')

    return parser.parse_args(args)



if __name__ == '__main__':
    main()
