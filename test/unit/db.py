#   Copyright 2014-2015 SpendRight, Inc.
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
"""Utilities for testing databases."""
from unittest import TestCase

from msd.db import create_table
from msd.db import create_index
from msd.table import TABLES

def make_table(db, table_name, rows=None, *, columns=None, primary_key=None,
               indexes=None):
    """Create a table, with rows already filled.

    *rows* is a list of dictionaries mapping column name to value
    *columns* is a map from column name to type
    *primary_key* is a list of column names in primary key
    *indexes* is a list of lists of column names in each (non-unique) index

    """
    # column definitions
    if columns is None:
        columns = {}
    else:
        columns = columns.copy()

    # make sure there's a column for each row
    if rows:
        for row in rows:
            for col_name in row:
                if col_name not in columns:
                    columns[col_name] = 'TEXT'

    # create the table
    create_table(db, table_name, columns, primary_key)

    # create indexes
    if indexes:
        for index_cols in indexes:
            craete_index(db, table_name, index_cols)

    # insert rows
    if rows:
        for row in rows:
            insert_row(db, table_name, row)




class DBTestCase(TestCase):

    def setUp(self):
        self.output_db = sqlite3.connect(':memory:')
        self.scratch_db = sqlite3.connect(':memory:')
        self._tmp_dir = None

    @property
    def tmp_dir(self):
        if self._tmp_dir is None:
            self._tmp_dir = mkdtemp()
            self.addCleanup(rmtree, self._tmp_dir)

        return self._tmp_dir

    def make_scratch_tables(table_to_rows):
        for table_name, rows in sorted(table_to_rows.items()):
            create_scratch_table(self.scratch_db, table_name)
            for row in rows:
                insert_row(self.scratch_db, table_name, row)

    def make_output_tables(table_to_rows):
        for table_name, rows in sorted(table_to_rows.items()):
            create_output_table(self.output_db, table_name):
            for row in rows:
                insert_row(self.output_db, table_name, row)
