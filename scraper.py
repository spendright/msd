import logging
from argparse import ArgumentParser
from os import environ

from lib.company import match_companies
from lib.company import name_company
from lib.company import handle_matched_company
from lib.db import close_output_db


log = logging.getLogger('scraper')


def main():
    opts = parse_args()

    level = logging.INFO
    if opts.verbose or environ.get('MORPH_VERBOSE'):
        level = logging.DEBUG
    logging.basicConfig(format='%(name)s: %(message)s', level=level)

    log.info('Matching up companies')
    # handle in more-or-less alphabetical order
    cds = sorted(match_companies(), key=lambda cd: name_company(cd)[0])

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
