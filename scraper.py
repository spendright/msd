import logging
from argparse import ArgumentParser

from lib.company import match_companies
from lib.company import name_company
from lib.company import handle_matched_company
from lib.db import close_output_db


log = logging.getLogger('scraper')


def main():
    opts = parse_args()

    level = logging.DEBUG if opts.verbose else logging.INFO
    logging.basicConfig(format='%(name)s: %(message)s', level=level)

    log.info('Matching up companies')
    named_cds = sorted((name_company(cd)[0], cd) for cd in match_companies())

    for name, cd in named_cds:
        log.info(name)
        company_record = handle_matched_company(cd)
        if company_record['company'] != name:
            log.info(u'  renamed to {}'.format(company_record['company']))
        log.debug(repr(company_record))

    close_output_db()


def parse_args(args=None):
    parser = ArgumentParser()
    parser.add_argument(
        '-v', '--verbose', dest='verbose', default=False, action='store_true',
        help='Enable debug logging')

    return parser.parse_args(args)



if __name__ == '__main__':
    main()
