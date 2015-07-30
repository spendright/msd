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


def insert_row(db, table_name, row):
    col_names, values = list(zip(*sorted(row.items())))

    insert_sql = 'INSERT INTO `{}` ({}) VALUES ({})'.format(
        table_name,
        ', '.join('`{}`'.format(col_name) for col_name in col_names),
        ', '.join('?' for _ in col_names))

    db.execute(insert_sql, values)


def open_db(path):
    """Open the sqlite database at the given path
    Use sqlite3.Row as our row_factory to wrap rows like dicts.
    """
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    return db


def show_tables(db):
    """List the tables in the given db."""
    sql = "SELECT name FROM sqlite_master WHERE type = 'table'"
    return sorted(row[0] for row in db.execute(sql))
