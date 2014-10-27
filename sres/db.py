# -*- coding: utf-8 -*-

#   Copyright 2014 David Marin
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
"""Download and open databases."""

import logging
import sqlite3
from dumptruck import DumpTruck
from os import environ
from os import rename
from os import remove
from os.path import exists
from urllib import urlencode

from srs.db import TABLE_TO_KEY_FIELDS
from srs.db import create_table_if_not_exists
from srs.db import show_tables
from srs.scrape import download


DB_TO_URL = {
    'campaigns': 'https://morph.io/spendright-scrapers/campaigns/data.sqlite',
    'companies': 'https://morph.io/spendright-scrapers/companies/data.sqlite',
}


MERGED_DB_FILENAME = 'merged.sqlite'
OUTPUT_DB_TMP_FILENAME = 'data.tmp.sqlite'
OUTPUT_DB_FILENAME = 'data.sqlite'

# used to indicate that a "campaign ID" actually refers to a company scraper
COMPANIES_PREFIX = 'companies:'



log = logging.getLogger(__name__)


def download_and_merge_dbs():
    if exists(MERGED_DB_FILENAME):
        remove(MERGED_DB_FILENAME)

    merged_db = sqlite3.connect(MERGED_DB_FILENAME)
    dt = DumpTruck(MERGED_DB_FILENAME)

    for db_name in sorted(DB_TO_URL):
        db = open_db(db_name)

        for table in show_tables(db.execute):
            if table not in TABLE_TO_KEY_FIELDS:
                log.warn('Unknown table `{}` in {} db, skipping'.format(
                    table, db_name))

            log.info('{}.{} -> {}'.format(db_name, table, MERGED_DB_FILENAME))

            create_table_if_not_exists(table, execute=merged_db.execute)

            for row in db.execute('SELECT * FROM `{}`'.format(table)):
                # prepend db name to scraper ID
                full_scraper_id = '{}:{}'.format(db_name, row['scraper_id'])
                row = dict(row, scraper_id=full_scraper_id)
                dt.upsert(row, table)


def open_db(name):
    if not hasattr(open_db, '_name_to_db'):
        open_db._name_to_db = {}

    if name not in open_db._name_to_db:
        filename = name + '.sqlite'
        if not exists(filename):
            if 'MORPH_API_KEY' not in environ:
                raise ValueError(
                    'Must set MORPH_API_KEY to download {} db'.format(name))

            url = DB_TO_URL[name] + '?' + urlencode(
                {'key': environ['MORPH_API_KEY']})

            log.info('downloading {} -> {}'.format(url, filename))
            download(url, filename)
        else:
            log.info('opening local copy of {}'.format(filename))

        db = sqlite3.connect(filename)
        db.row_factory = sqlite3.Row
        open_db._name_to_db[name] = db

    return open_db._name_to_db[name]


def open_output_db():
    """Open a DB for output into a temp file.

    If we haven't already opened it, initialize its tables."""
    if not hasattr(open_output_db, '_db'):
        if exists(OUTPUT_DB_TMP_FILENAME):
            log.debug('Removing old version of {}'.format(
                OUTPUT_DB_TMP_FILENAME))
            remove(OUTPUT_DB_TMP_FILENAME)

        log.debug('Opening {}'.format(OUTPUT_DB_TMP_FILENAME))
        db = sqlite3.connect(OUTPUT_DB_TMP_FILENAME)

        # init tables
        for table in sorted(TABLE_TO_KEY_FIELDS):
            create_table_if_not_exists(
                table, with_scraper_id=False, execute=db.execute)

        open_output_db._db = db

    return open_output_db._db


def open_output_dump_truck():
    if not hasattr(open_output_dump_truck, '_dump_truck'):
        open_output_db()
        open_output_dump_truck._dump_truck = DumpTruck(OUTPUT_DB_TMP_FILENAME)

    return open_output_dump_truck._dump_truck


def output_row(row, table):
    row = clean_row(row)
    log.debug('{}: {}'.format(table, repr(row)))

    dt = open_output_dump_truck()
    dt.upsert(row, table)


def close_output_db():
    """Move output_db into place."""
    log.debug('Closing {} and renaming to {}'.format(
        OUTPUT_DB_TMP_FILENAME, OUTPUT_DB_FILENAME))

    open_output_db._db.close()
    if hasattr(open_output_db, '_db'):
        del open_output_db._db
    if hasattr(open_output_dump_truck, '_dump_truck'):
        del open_output_dump_truck._dump_truck

    rename(OUTPUT_DB_TMP_FILENAME, OUTPUT_DB_FILENAME)


def clean_row(row):
    """Convert a row to a dict, strip None values."""
    if row is None:
        return None

    row = dict((k, row[k]) for k in row.keys() if row[k] is not None)

    # TODO: kind of a hack to make company scrapers look like campaign scrapers
    if 'scraper_id' in row:
        row['campaign_id'] = COMPANIES_PREFIX + row.pop('scraper_id')

    return row


def select_brands(campaign_id, company):
    if campaign_id.startswith(COMPANIES_PREFIX):
        scraper_id = campaign_id[len(COMPANIES_PREFIX):]

        db = open_db('companies')
        cursor = db.execute(
            'SELECT * FROM brand WHERE scraper_id = ?'
            ' AND company = ?', [scraper_id, company])
    else:
        db = open_db('campaigns')
        cursor = db.execute(
            'SELECT * FROM campaign_brand WHERE campaign_id = ?'
            ' AND company = ?', [campaign_id, company])

    return [clean_row(row) for row in cursor]


def select_brand_ratings(campaign_id, company, brand):
    if campaign_id.startswith(COMPANIES_PREFIX):
        return []

    db = open_db('campaigns')

    return [clean_row(row) for row in
            db.execute(
                'SELECT * FROM campaign_brand_rating WHERE campaign_id = ?'
                ' AND company = ? AND brand = ?',
                [campaign_id, company, brand])]


def select_company(campaign_id, company):
    if campaign_id.startswith(COMPANIES_PREFIX):
        scraper_id = campaign_id[len(COMPANIES_PREFIX):]

        db = open_db('companies')
        cursor = db.execute(
            'SELECT * FROM company WHERE scraper_id = ?'
            ' AND company = ?', [scraper_id, company])
    else:
        db = open_db('campaigns')
        cursor = db.execute(
            'SELECT * FROM campaign_company WHERE campaign_id = ?'
            ' AND company = ?', [campaign_id, company])

    return clean_row(cursor.fetchone())


def select_company_ratings(campaign_id, company):
    if campaign_id.startswith(COMPANIES_PREFIX):
        return []

    db = open_db('campaigns')

    return [clean_row(row) for row in
            db.execute(
                'SELECT * FROM campaign_company_rating WHERE campaign_id = ?'
                ' AND company = ?',
                [campaign_id, company])]


def select_all_campaigns():
    db = open_db('campaigns')

    return [clean_row(row) for row in
            db.execute('SELECT * FROM campaign ORDER BY campaign_id')]


def select_all_categories():
    campaigns_db = open_db('campaigns')
    for campaign_id, category in campaigns_db.execute(
            'SELECT campaign_id, category'
            ' FROM campaign_brand_category UNION '
            'SELECT campaign_id, category'
            ' FROM campaign_company_category'
            ' GROUP BY campaign_id, category'):
        yield campaign_id, category

    companies_db = open_db('companies')
    for scraper_id, category in companies_db.execute(
            'SELECT scraper_id, category FROM brand_category UNION '
            'SELECT scraper_id, category FROM company_category'
            ' GROUP BY category'):
        yield COMPANIES_PREFIX + scraper_id, category



def select_all_companies():
    campaigns_db = open_db('campaigns')
    for campaign_id, company in campaigns_db.execute(
            'SELECT campaign_id, company from campaign_company'):
        yield campaign_id, company

    companies_db = open_db('companies')
    for scraper_id, company in companies_db.execute(
            'SELECT scraper_id, company from company'):
        yield COMPANIES_PREFIX + scraper_id, company


def select_company_categories(campaign_id, company):
    if campaign_id.startswith(COMPANIES_PREFIX):
        scraper_id = campaign_id[len(COMPANIES_PREFIX):]

        db = open_db('companies')
        cursor = db.execute('SELECT * from company_category'
                            ' WHERE scraper_id = ? AND company = ?',
                            [scraper_id, company])
    else:
        db = open_db('campaigns')
        cursor = db.execute('SELECT * from campaign_company_category'
                            ' WHERE campaign_id = ? AND company = ?',
                            [campaign_id, company])

    return [clean_row(row) for row in cursor]


def select_brand_categories(campaign_id, company, brand):
    if campaign_id.startswith(COMPANIES_PREFIX):
        scraper_id = campaign_id[len(COMPANIES_PREFIX):]

        db = open_db('companies')
        cursor = db.execute('SELECT * from brand_category'
                            ' WHERE scraper_id = ? AND company = ?'
                            ' AND brand = ?',
                            [scraper_id, company, brand])
    else:
        db = open_db('campaigns')
        cursor = db.execute('SELECT * from campaign_brand_category'
                            ' WHERE campaign_id = ? AND company = ?'
                            ' AND brand = ?',
                            [campaign_id, company, brand])

    return [clean_row(row) for row in cursor]
