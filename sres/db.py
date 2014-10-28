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
from os.path import getmtime

from srs.db import DEFAULT_DB_NAME
from srs.db import TABLE_TO_KEY_FIELDS
from srs.db import create_table_if_not_exists
from srs.db import download_db
from srs.db import get_db_path
from srs.db import open_db
from srs.db import open_dt
from srs.db import show_tables


SOURCE_DBS = {
    'campaigns',
    'companies',
}

CAMPAIGNS_PREFIX = 'campaigns:'

INPUT_DB_NAME = 'input'
INPUT_DB_TMP_NAME = INPUT_DB_NAME + '.tmp'

OUTPUT_DB_NAME = DEFAULT_DB_NAME + '.tmp'

URLS_DB_NAME = 'urls'

log = logging.getLogger(__name__)


def download_and_merge_dbs(force=False):
    """Download the various scraper DBs and merge into a single
    "input" DB."""
    # if input DB already exists and all its deps are up-to-date, we're done
    input_db_path = get_db_path(INPUT_DB_NAME)
    if exists(input_db_path) and not force:
        mtime = getmtime(input_db_path)
        if all(exists(db_path) and getmtime(db_path) < mtime for db_path
               in (get_db_path(db_name) for db_name in SOURCE_DBS)):
            return

    input_db_tmp_path = get_db_path(INPUT_DB_TMP_NAME)
    if exists(input_db_tmp_path):
        log.debug('Removing old version of {}'.format(input_db_tmp_path))
        remove(input_db_tmp_path)

    db = open_db(INPUT_DB_TMP_NAME)
    dt = open_dt(INPUT_DB_TMP_NAME)

    for src_db_name in sorted(SOURCE_DBS):
        download_db(src_db_name, force=force)
        src_db = open_db(src_db_name)

        for table in show_tables(src_db):
            if table not in TABLE_TO_KEY_FIELDS:
                log.warn('Unknown table `{}` in {} db, skipping'.format(
                    table, src_db_name))

            log.info('{}.{} -> {}'.format(src_db_name, table, input_db_path))

            create_table_if_not_exists(table, db=db)

            for row in src_db.execute('SELECT * FROM `{}`'.format(table)):
                # prepend db name to scraper ID
                scraper_id = '{}:{}'.format(src_db_name, row['scraper_id'])
                row = dict(row, scraper_id=scraper_id)
                dt.upsert(row, table)

    log.info('closing {} and moving to {}'.format(
        input_db_tmp_path, input_db_path))
    db.close()
    dt.close()
    rename(input_db_tmp_path, input_db_path)


def open_input_db():
    # TODO: does it actually save us anything to cache the input db?
    if not hasattr(open_input_db, '_db'):
        open_input_db._db = open_db(INPUT_DB_NAME)

    return open_input_db._db


def init_output_db():
    """Create a fresh output DB and its tables."""
    output_db_path = get_db_path(OUTPUT_DB_NAME)

    if exists(output_db_path):
        log.debug('Removing old version of {}'.format(
            output_db_path))
        remove(output_db_path)

    open_output_db()


def open_output_db():
    """Open a DB for output into a temp file."""
    if not hasattr(open_output_db, '_db'):
        open_output_db._db = open_db(OUTPUT_DB_NAME)

    return open_output_db._db


def open_output_dt():
    """Get the DumpTruck for the output DB"""
    if not hasattr(open_output_dt, '_dt'):
        open_output_db()
        open_output_dt._dt = open_dt(OUTPUT_DB_NAME)

    return open_output_dt._dt


def open_urls_db():
    """Open urls.sqlite, downloading it if necessary."""
    if not hasattr(open_urls_db, '_db'):
        download_db(URLS_DB_NAME)
        open_urls_db._db = open_db(URLS_DB_NAME)

    return open_urls_db._db


def output_row(row, table):
    row = clean_row(row)
    log.debug('{}: {}'.format(table, repr(row)))

    dt = open_output_dt()
    dt.upsert(row, table)


def close_output_db():
    """Move output_db into place."""
    output_db_path = get_db_path(OUTPUT_DB_NAME)
    default_db_path = get_db_path(DEFAULT_DB_NAME)

    log.debug('Closing {} and renaming to {}'.format(
        output_db_path, default_db_path))

    open_output_db._db.close()
    if hasattr(open_output_db, '_db'):
        del open_output_db._db
    if hasattr(open_output_dt, '_dt'):
        del open_output_dt._dt

    rename(output_db_path, default_db_path)


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


def select_categories():
    db = open_input_db()

    return [clean_row(row) for row in
            db.execute('SELECT * FROM category ORDER BY scraper_id, category')]


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


def select_url(url):
    db = open_urls_db()

    cursor = db.execute('SELECT * from url WHERE url = ?', [url])

    row = cursor.fetchone()

    if row:
        return clean_row(row)
    else:
        return None
