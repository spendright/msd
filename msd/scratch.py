# Copyright 2014-2016 SpendRight, Inc.
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
"""Building the scratch (intermediate) database."""
import re
import yaml
from logging import getLogger
from os import remove
from os import rename
from os.path import exists
from os.path import getmtime

from .db import create_index
from .db import create_table
from .db import insert_row
from .db import open_db
from .db import show_tables
from .norm import clean_string
from .table import TABLES

log = getLogger(__name__)


_INPUT_PATH_RE = re.compile(
    r'^(?P<scraper_prefix>.*)\.(?P<extension>(sqlite|yaml))$', re.I)


def build_scratch_db(
        scratch_db_path, input_db_paths, *, force=False):
    """Take data from the various input databases, and put it into
    a single, indexed database with correct table definitions.

    Does nothing if the scratch DB is newer than all the input
    DBs, unless *force* is true.

    Unlike the output database, every table in the scratch database
    has a scraper_id field. The names of each input database are used
    as a "namespace" which is prepended to the scraper_id value
    (if any) in the input data. For example a row with scraper_id
    "coca_cola" from a db named sr.company.sqlite would end up in
    the scratch DB with scraper_id value "sr.company.coca_cola".

    This also cleans smart quotes, excess whitespace, etc. out of the
    input data.
    """
    # TODO: might also want to apply custom corrections here
    if exists(scratch_db_path) and not force:
        mtime = getmtime(scratch_db_path)
        if all(exists(db_path) and getmtime(db_path) < mtime
               for db_path in input_db_paths):
            log.info('{} already exists and is up-to-date'.format(
                scratch_db_path))
            return

    scratch_db_tmp_path = scratch_db_path + '.tmp'
    if exists(scratch_db_tmp_path):
        remove(scratch_db_tmp_path)

    log.info('building {}...'.format(scratch_db_tmp_path))

    with open_db(scratch_db_tmp_path) as scratch_db:

        create_scratch_tables(scratch_db)

        for input_db_path in input_db_paths:
            log.info('dumping data from {} -> {}'.format(
                input_db_path, scratch_db_tmp_path))

            scraper_prefix, file_type = parse_input_path(input_db_path)

            if file_type == 'sqlite':
                with open_db(input_db_path) as input_db:
                    dump_db_to_scratch(input_db, scratch_db, scraper_prefix)
            else:
                assert file_type == 'yaml'
                with open(input_db_path, mode='rb') as input_yaml:
                    dump_yaml_to_scratch(
                        input_yaml, scratch_db, scraper_prefix)

    log.info('moving {} -> {}'.format(scratch_db_tmp_path, scratch_db_path))
    rename(scratch_db_tmp_path, scratch_db_path)


def create_scratch_tables(scratch_db):
    """Add tables to the given (open) SQLite DB."""
    for table_name in sorted(TABLES):
        create_scratch_table(scratch_db, table_name)


def create_scratch_table(scratch_db, table_name):
    table_def = TABLES[table_name]

    columns = table_def['columns'].copy()
    columns['scraper_id'] = 'text'

    create_table(scratch_db, table_name, columns)

    # add "primary key" (non-unique) index
    index_cols = list(table_def.get('primary_key', ()))
    if 'scraper_id' not in index_cols:
        index_cols = ['scraper_id'] + index_cols
    create_index(scratch_db, table_name, index_cols)

    # add other indexes
    for index_cols in table_def.get('indexes', ()):
        create_index(scratch_db, table_name, index_cols)


def parse_input_path(path):
    """Parse an input path into (scraper_prefix, file_type), or raise
    ValueError.

    file_type will be one of 'sqlite' or 'yaml'
    """
    m = _INPUT_PATH_RE.match(path)
    if not m:
        raise ValueError('Unknown input file type: {}'.format(path))
    return m.group('scraper_prefix'), m.group('extension').lower()


def dump_db_to_scratch(input_db, scratch_db, scraper_prefix=''):
    input_table_names = set(show_tables(input_db))

    for table_name in sorted(input_table_names):
        if table_name in TABLES:
            select_sql = 'SELECT * from `{}`'.format(table_name)
            rows = input_db.execute(select_sql)
        else:
            # don't even bother reading tables that dump_db_to_scratch()
            # will ignore
            rows = ()

        dump_table_to_scratch(table_name, rows, scratch_db, scraper_prefix)


def dump_yaml_to_scratch(input_yaml, scratch_db, scraper_prefix):
    data = yaml.load(input_yaml)

    if not isinstance(data, dict):
        raise TypeError('Expected YAML to be dictionary')

    for table_name, rows in sorted(data.items()):
        if not isinstance(rows, list):
            raise TypeError(
                'Expected rows for table {} to be list'.format(table_name))

        dump_table_to_scratch(table_name, rows, scratch_db, scraper_prefix)


def dump_table_to_scratch(table_name, rows, scratch_db, scraper_prefix):
    if table_name not in TABLES:
        log.info('  ignoring extra table: {}'.format(table_name))
        return

    log.info('  dumping table: {}'.format(table_name))

    table_def = TABLES[table_name]

    for i, row in enumerate(rows):
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



def scratch_tables_with_cols(cols):
    cols = set(cols)
    return [table_name for table_name, table_def in sorted(TABLES.items())
            if not (cols - set(table_def['columns']) - {'scraper_id'})]


def get_distinct_values(scratch_db, cols):
    """Get all distinct values of the given list of columns from
    any table that has all of the given columns."""
    values = set()

    for table_name in scratch_tables_with_cols(cols):
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
    column_types = table_def.get('columns', {})
    valid_cols = set(column_types) | {'scraper_id'}

    cleaned = {}

    for col_name, value in sorted(row.items()):
        if col_name not in valid_cols:
            continue

        if isinstance(value, str):
            value = clean_string(value)

        cleaned[col_name] = value

    # make sure primary key columns aren't null or unset
    for key_col_name in table_def.get('primary_key', ()):
        if cleaned.get(key_col_name) is None:
            if column_types.get(key_col_name) == 'text':
                cleaned[key_col_name] = ''
            # currently all our primary key columns are text

    return cleaned
