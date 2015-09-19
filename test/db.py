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
import sqlite3
from unittest import TestCase

from msd.db import create_table
from msd.db import create_index
from msd.db import insert_row
from msd.db import open_db
from msd.merge import create_output_table
from msd.scratch import create_scratch_table
from msd.table import TABLES


# stuff that could be in msd.db, but that we only use for testing

def select_all(db, table_name):
    """Get all rows from a table, and sort (for easy testing of equality)."""
    return sorted_rows(
        dict(row) for row in
        db.execute('SELECT * FROM `{}`'.format(table_name)))


def sorted_rows(rows):
    """Sort rows by the value of each key, in alphabetical order
    (for easy testing of equality)."""
    # avoid comparing values of different types; Python 3 dislikes this
    return sorted(
        rows,
        key=lambda row: sorted((k, (type(v).__name__, v))
                               for (k, v) in row.items()))


def strip_null(row):
    """Remove keys from *row* whose values are ``None``."""
    return dict((k, v) for k, v in row.items() if v is not None)


def insert_rows(db, table_name, rows):
    """Call insert_row() multiple times. Would want to use multi-row
    insert syntax before putting this in msd.db (but we don't actually
    need it)."""
    for row in rows:
        insert_row(db, table_name, row)



class DBTestCase(TestCase):

    # output_tables to create at setup time
    OUTPUT_TABLES = []

    # scratch tables to create at setup time
    SCRATCH_TABLES = []

    def setUp(self):
        self.output_db = open_db(':memory:')
        self.scratch_db = open_db(':memory:')
        self._tmp_dir = None

        for table_name in self.SCRATCH_TABLES:
            create_scratch_table(self.scratch_db, table_name)

        for table_name in self.OUTPUT_TABLES:
            create_output_table(self.output_db, table_name)

    @property
    def tmp_dir(self):
        if self._tmp_dir is None:
            self._tmp_dir = mkdtemp()
            self.addCleanup(rmtree, self._tmp_dir)

        return self._tmp_dir
