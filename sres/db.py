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
from os import rename
from os import remove
from os.path import exists

from srs.db import DB_FILE_EXT
from srs.db import DEFAULT_DB_NAME
from srs.db import DEFAULT_DB_PATH
from srs.db import TABLE_TO_KEY_FIELDS
from srs.db import create_table_if_not_exists
from srs.db import download_db
from srs.db import open_db
from srs.db import open_dt
from srs.db import show_tables

SOURCE_DBS = {
    'campaigns',
    'companies',
}

# TODO: use scraper_id instead
COMPANIES_PREFIX = None

RAW_DB_NAME = 'raw'
RAW_DB_PATH = RAW_DB_NAME + DB_FILE_EXT

TMP_DB_NAME = DEFAULT_DB_NAME + '.tmp'
TMP_DB_PATH = TMP_DB_NAME + DB_FILE_EXT


log = logging.getLogger(__name__)


def download_and_merge_dbs():
    if exists(RAW_DB_PATH):
        log.debug('Removing old version of {}'.format(RAW_DB_PATH))
        remove(RAW_DB_PATH)

    db = open_db(RAW_DB_NAME)
    dt = open_dt(RAW_DB_NAME)

    for src_db_name in sorted(SOURCE_DBS):
        download_db(src_db_name)
        src_db = open_db(src_db_name)

        for table in show_tables(src_db):
            if table not in TABLE_TO_KEY_FIELDS:
                log.warn('Unknown table `{}` in {} db, skipping'.format(
                    table, src_db_name))

            log.info('{}.{} -> {}'.format(src_db_name, table, RAW_DB_PATH))

            create_table_if_not_exists(table, db=db)

            for row in db.execute('SELECT * FROM `{}`'.format(table)):
                # prepend db name to scraper ID
                scraper_id = '{}:{}'.format(src_db_name, row['scraper_id'])
                row = dict(row, scraper_id=scraper_id)
                dt.upsert(row, table)


def open_raw_db():
    return open_db(RAW_DB_NAME)


def open_output_db():
    """Open a DB for output into a temp file.

    If we haven't already opened it, initialize its tables."""
    if not hasattr(open_output_db, '_db'):
        if exists(TMP_DB_PATH):
            log.debug('Removing old version of {}'.format(
                TMP_DB_PATH))
            remove(TMP_DB_PATH)

        db = open_db(TMP_DB_NAME)

        # init tables
        for table in sorted(TABLE_TO_KEY_FIELDS):
            create_table_if_not_exists(
                table, with_scraper_id=False, db=db)

        open_output_db._db = db

    return open_output_db._db


def open_output_dt():
    """Get the DumpTruck for the output DB"""
    if not hasattr(open_output_dt, '_dt'):
        open_output_db()
        open_output_dt._dt = open_dt(TMP_DB_NAME)

    return open_output_dt._dt


def output_row(row, table):
    row = clean_row(row)
    log.debug('{}: {}'.format(table, repr(row)))

    dt = open_output_dt()
    dt.upsert(row, table)


def close_output_db():
    """Move output_db into place."""
    log.debug('Closing {} and renaming to {}'.format(
        TMP_DB_PATH, DEFAULT_DB_PATH))

    open_output_db._db.close()
    if hasattr(open_output_db, '_db'):
        del open_output_db._db
    if hasattr(open_output_dt, '_dt'):
        del open_output_dt._dt

    rename(TMP_DB_PATH, DEFAULT_DB_PATH)


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
