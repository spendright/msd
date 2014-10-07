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

CAMPAIGNS_PREFIX = 'campaigns:'

INPUT_DB_NAME = 'input'
INPUT_DB_PATH = INPUT_DB_NAME + DB_FILE_EXT

OUTPUT_DB_NAME = DEFAULT_DB_NAME + '.tmp'
OUTPUT_DB_PATH = OUTPUT_DB_NAME + DB_FILE_EXT


log = logging.getLogger(__name__)


def download_and_merge_dbs():
    """Download the various scraper DBs and merge into a single
    "input" DB."""
    if exists(INPUT_DB_PATH):
        log.debug('Removing old version of {}'.format(INPUT_DB_PATH))
        remove(INPUT_DB_PATH)

    db = open_db(INPUT_DB_NAME)
    dt = open_dt(INPUT_DB_NAME)

    for src_db_name in sorted(SOURCE_DBS):
        download_db(src_db_name)
        src_db = open_db(src_db_name)

        for table in show_tables(src_db):
            if table not in TABLE_TO_KEY_FIELDS:
                log.warn('Unknown table `{}` in {} db, skipping'.format(
                    table, src_db_name))

            log.info('{}.{} -> {}'.format(src_db_name, table, INPUT_DB_PATH))

            create_table_if_not_exists(table, db=db)

            for row in db.execute('SELECT * FROM `{}`'.format(table)):
                # prepend db name to scraper ID
                scraper_id = '{}:{}'.format(src_db_name, row['scraper_id'])
                row = dict(row, scraper_id=scraper_id)
                dt.upsert(row, table)


def open_input_db():
    # TODO: does it actually save us anything to cache the input db?
    if not hasattr(open_input_db, '_db'):
        open_input_db._db = open_input_db(INPUT_DB_NAME)

    return open_input_db._db


def open_output_db():
    """Open a DB for output into a temp file.

    If we haven't already opened it, initialize its tables."""
    if not hasattr(open_output_db, '_db'):
        if exists(OUTPUT_DB_PATH):
            log.debug('Removing old version of {}'.format(
                OUTPUT_DB_PATH))
            remove(OUTPUT_DB_PATH)

        db = open_db(OUTPUT_DB_NAME)

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
        open_output_dt._dt = open_dt(OUTPUT_DB_NAME)

    return open_output_dt._dt


def output_row(row, table):
    row = clean_row(row)
    log.debug('{}: {}'.format(table, repr(row)))

    dt = open_output_dt()
    dt.upsert(row, table)


def close_output_db():
    """Move output_db into place."""
    log.debug('Closing {} and renaming to {}'.format(
        OUTPUT_DB_PATH, DEFAULT_DB_PATH))

    open_output_db._db.close()
    if hasattr(open_output_db, '_db'):
        del open_output_db._db
    if hasattr(open_output_dt, '_dt'):
        del open_output_dt._dt

    rename(OUTPUT_DB_PATH, DEFAULT_DB_PATH)


def clean_row(row):
    """Convert a row to a dict, strip None values."""
    if row is None:
        return None

    row = dict((k, row[k]) for k in row.keys() if row[k] is not None)

    return row


def select_brands(scraper_id, company):
    db = open_input_db()

    cursor = db.execute(
        'SELECT * FROM brand WHERE scraper_id = ?'
        ' AND company = ?', [scraper_id, company])

    return [clean_row(row) for row in cursor]


def select_brand_ratings(scraper_id, company, brand):
    # campaign_id is derived from scraper_id
    if not scraper_id.startswith(CAMPAIGNS_PREFIX):
        return []
    campaign_id = scraper_id[len(CAMPAIGNS_PREFIX):]

    db = open_input_db()

    return [clean_row(row) for row in
            db.execute(
                'SELECT * FROM campaign_brand_rating WHERE'
                ' scraper_id = ? AND campaign_id = ?'
                ' AND company = ? AND brand = ?',
                [scraper_id, campaign_id, company, brand])]


def select_company(scraper_id, company):
    db = open_input_db()

    cursor = db.execute(
        'SELECT * FROM company WHERE scraper_id = ?'
        ' AND company = ?', [scraper_id, company])

    return clean_row(cursor.fetchone())


def select_company_ratings(scraper_id, company):
    # campaign_id is derived from scraper_id
    if not scraper_id.startswith(CAMPAIGNS_PREFIX):
        return []
    campaign_id = scraper_id[len(CAMPAIGNS_PREFIX):]

    db = open_input_db()

    return [clean_row(row) for row in
            db.execute(
                'SELECT * FROM campaign_company_rating WHERE'
                ' scraper_id = ? AND campaign_id = ?'
                ' AND company = ?',
                [scraper_id, campaign_id, company])]


def select_all_campaigns():
    db = open_input_db()

    return [clean_row(row) for row in
            db.execute('SELECT * FROM campaign ORDER BY campaign_id')]


def select_all_categories():
    db = open_input_db()

    for scraper_id, category in db.execute(
            'SELECT scraper_id, category FROM brand_category UNION '
            'SELECT scraper_id, category FROM company_category'
            ' GROUP BY category'):
        yield scraper_id, category


def select_all_companies():
    db = open_input_db()

    for scraper_id, company in db.execute(
            'SELECT scraper_id, company from company'):
        yield scraper_id, company


def select_company_categories(scraper_id, company):
    db = open_input_db()

    cursor = db.execute('SELECT * from company_category'
                        ' WHERE scraper_id = ? AND company = ?',
                        [scraper_id, company])

    return [clean_row(row) for row in cursor]


def select_brand_categories(scraper_id, company, brand):
    db = open_input_db()

    cursor = db.execute('SELECT * from brand_category'
                        ' WHERE scraper_id = ? AND company = ?'
                        ' AND brand = ?',
                        [scraper_id, company, brand])

    return [clean_row(row) for row in cursor]
