import logging
from argparse import ArgumentParser
from os import environ

from lib.company import match_companies
from lib.company import name_company
from lib.company import handle_matched_company
from lib.db import output_row
from lib.db import close_output_db
from lib.db import select_all_campaigns


log = logging.getLogger('scraper')


def main():
    opts = parse_args()

    level = logging.INFO
    if opts.verbose or environ.get('MORPH_VERBOSE'):
        level = logging.DEBUG
    logging.basicConfig(format='%(name)s: %(message)s', level=level)

    # campaigns
    log.info('Outputting campaign table')
    for campaign_row in select_all_campaigns():
        log.info(campaign_row['campaign_id'])
        output_row(campaign_row, 'campaign')

    log.info('Matching up companies')
    # handle in more-or-less alphabetical order
    cds = sorted(match_companies(), key=lambda cd: name_company(cd)[0])

    log.info('Outputting company data (all other tables)')
    for cd in cds:
        handle_matched_company(cd)

    close_output_db()


def parse_args(args=None):
    parser = ArgumentParser()
    parser.add_argument(
        '-v', '--verbose', dest='verbose', default=False, action='store_true',
        help='Enable debug logging')

    return parser.parse_args(args)



if __name__ == '__main__':
    main()
