import codecs
import logging
from sys import stdout

from lib.company import get_companies
from lib.company import match_company_names


log = logging.getLogger('scraper')


def main():
    logging.basicConfig(format='%(name)s: %(message)s', level=logging.INFO)

    companies = get_companies()
    sn2info = match_company_names(companies)

    out = codecs.getwriter('utf8')(stdout)
    for sn, info in sorted(sn2info.items()):
        line = sn
        if info['company_full'] != sn:
            line += u' ({})'.format(info['company_full'])

        other_names = [c for c in info['companies']
                       if c not in (sn, info['company_full'])]
        if other_names:
            line += u': {}'.format('; '.join(other_names))

        out.write(line + '\n')


if __name__ == '__main__':
    main()
