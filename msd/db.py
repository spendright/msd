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
import sqlite3
from itertools import groupby


def create_table(db, table_name, columns, primary_key=None):
    """Create a table with the given columns and, optionally, primary key.

    *columns* is a map from column name to type
    *primary_key* is a list of column names
    """

    col_def_sql = ', '.join('`{}` {}'.format(col_name, col_type)
                            for col_name, col_type in sorted(columns.items()))

    # optional PRIMARY KEY
    primary_key_sql = ''
    if primary_key:
        primary_key_sql = ', PRIMARY KEY({})'.format(col_sql(primary_key))

    create_sql = 'CREATE TABLE `{}` ({}{})'.format(
        table_name, col_def_sql, primary_key_sql)

    db.execute(create_sql)


def create_index(db, table_name, index_cols):
    if isinstance(index_cols, str):
        raise TypeError

    index_name = '_'.join([table_name] + list(index_cols))
    index_sql = 'CREATE INDEX `{}` ON `{}` ({})'.format(
            index_name, table_name, ', '.join(
                '`{}`'.format(ic) for ic in index_cols))

    db.execute(index_sql)


def col_sql(col_names):
    """Convert a list of column names to SQL."""
    return ', '.join('`{}`'.format(col_name) for col_name in col_names)


def insert_row(db, table_name, row):
    col_names, values = list(zip(*sorted(row.items())))

    insert_sql = 'INSERT INTO `{}` ({}) VALUES ({})'.format(
        table_name,
        col_sql(col_names),
        ', '.join('?' for _ in col_names))

    db.execute(insert_sql, values)


def open_db(path):
    """Open the sqlite database at the given path
    Use sqlite3.Row as our row_factory to wrap rows like dicts.
    """
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def select_groups(db, table_name, key_cols, cols=None):
    """Select all rows in the given table. Yield tuples of
    (key, [rows]), where key is the values of the various key
    columns, and rows is a list of all rows with those values, as dicts.
    """
    if isinstance(key_cols, str):
        raise TypeError

    from_cols_sql = col_sql(cols) if cols else '*'
    key_sql = col_sql(key_cols)

    select_sql = 'SELECT {} FROM `{}` ORDER BY {}'.format(
        from_cols_sql, table_name, key_sql)

    for key, rows in groupby(
            db.execute(select_sql),
            key=lambda r: tuple(r[kc] for kc in key_cols)):

        yield key, [dict(row) for row in rows]


def show_tables(db):
    """List the tables in the given db."""
    sql = "SELECT name FROM sqlite_master WHERE type = 'table'"
    return sorted(row[0] for row in db.execute(sql))
