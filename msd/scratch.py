# Copyright 2014-2015 SpendRight, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from logging import getLogger
from os import remove
from os import rename
from os.path import exists
from os.path import getmtime

from msd.clean import clean_value
from msd.db import insert_row
from msd.db import open_db
from msd.db import show_tables
from msd.table import TABLES

log = getLogger(__name__)


def build_scratch_db(
        input_db_paths, scratch_db_path, *, force=False):

    if exists(scratch_db_path) and not force:
        mtime = getmtime(scratch_db_path)
        if all(exists(db_path) and getmtime(db_path) < mtime
               for db_path in input_db_paths):
            log.info('{} already exists and is up-to-date'.format(
                scratch_db_path))
            return

    log.info('building {}'.format(scratch_db_path))

    tmp_scratch_db_path = scratch_db_path + '.tmp'
    if exists(tmp_scratch_db_path):
        remove(tmp_scratch_db_path)

    with open_db(tmp_scratch_db_path) as scratch_db:

        init_scratch_tables(scratch_db)

        for input_db_path in input_db_paths:
            log.info('dumping data from {} -> {}'.format(
                input_db_path, tmp_scratch_db_path))

            scraper_prefix = db_path_to_scraper_prefix(input_db_path)
            with open_db(input_db_path) as input_db:

                dump_db_to_scratch(input_db, scratch_db, scraper_prefix)

    log.info('moving {} -> {}'.format(tmp_scratch_db_path, scratch_db_path))
    rename(tmp_scratch_db_path, scratch_db_path)


def init_scratch_tables(db):
    """Add tables to the given (open) SQLite DB."""
    for table_name, table_def in sorted(TABLES.items()):
        columns = table_def['columns'].copy()
        columns['scraper_id'] = 'text'

        create_sql = 'CREATE TABLE `{}` ({})'.format(
            table_name, ', '.join(
                '`{}` {}'.format(col_name, col_type)
                for col_name, col_type in sorted(columns.items())))
        db.execute(create_sql)

        index_cols = list(table_def.get('primary_key') or ())
        if 'scraper_id' not in index_cols:
            index_cols = ['scraper_id'] + index_cols
        index_name = '_'.join([table_name] + index_cols)

        index_sql = 'CREATE INDEX `{}` ON `{}` ({})'.format(
            index_name, table_name, ', '.join(
                '`{}`'.format(ic) for ic in index_cols))

        db.execute(index_sql)


def db_path_to_scraper_prefix(path):
    idx = path.lower().rfind('.sqlite')
    if idx == -1:
        raise ValueError
    return path[:idx]


def dump_db_to_scratch(input_db, scratch_db, scraper_prefix=''):
    input_table_names = set(show_tables(input_db))

    extra_table_names = input_table_names - set(TABLES)
    if extra_table_names:
        log.info('  ignoring extra tables: {}'.format(
            ', '.join(extra_table_names)))

    for table_name in sorted(TABLES):
        if table_name in input_table_names:
            dump_table_to_scratch(
                input_db, table_name, scratch_db, scraper_prefix)


def dump_table_to_scratch(input_db, table_name, scratch_db, scraper_prefix):
    log.info('  dumping table: {}'.format(table_name))

    table_def = TABLES[table_name]

    select_sql = 'SELECT * from `{}`'.format(table_name)
    for i, row in enumerate(input_db.execute(select_sql)):
        row = dict(row)

        # deal with extra columns
        if i == 0:  # only need to check once
            expected_cols = set(table_def['columns']) | {'scraper_id'}
            extra_cols = sorted(set(row) - expected_cols)
            if extra_cols:
                log.info('  ignoring extra columns in {}: {}'.format(
                    table_name, ', '.join(extra_cols)))

        # clean ugly data, dump extra columns
        row = clean_input_row(row, table_name)

        # pick scraper_id
        if 'scraper_id' in row:
            row['scraper_id'] = scraper_prefix + '.' + row['scraper_id']
        else:
            row['scraper_id'] = scraper_prefix

        # insert!
        insert_row(scratch_db, table_name, row)


def select_distinct_values(scratch_db, cols):
    """Get all distinct values of the given list of columns from
    any table that has all of the given columns."""
    values = set()

    for table_name, table_def in sorted(TABLES.items()):
        # skip tables that don't have all the columns
        if set(cols) - set(table_def['columns']) - {'scraper_id'}:
            continue

        cols_sql = ', '.join('`{}`'.format(col) for col in cols)

        select_sql = 'SELECT {} FROM `{}` GROUP BY {}'.format(
            cols_sql, table_name, cols_sql)
        for row in scratch_db.execute(select_sql):
            values.add(tuple(row))

    return values


def clean_input_row(row, table_name):
    """Clean each value in the given row of input data, and remove
    extra columns."""
    table_def = TABLES.get(table_name, {})
    valid_cols = set(table_def.get('columns', ())) | {'scraper_id'}
    clean_kwarg_map = table_def.get('clean_kwargs', {})

    return dict(
        (col_name, clean_value(value,
                               **clean_kwarg_map.get(col_name, {})))
        for col_name, value in row.items()
        if col_name in valid_cols)
