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
"""Supporting code to merge data from the scratch table and write it
to the output table."""
from msd.table import TABLES


def create_output_table(output_db, table_name):
    table_def = TABLES[table_name]
    columns = table_def['columns']
    primary_key = table_def['primary_key']

    create_sql = 'CREATE TABLE `{}` ({}, PRIMARY KEY ({}))'.format(
        table_name,
        ', '.join('`{}` {}'.format(col_name, col_type)
                  for col_name, col_type in sorted(columns.items())),
        ', '.join('`{}`'.format(pk_col) for pk_col in primary_key))
    output_db.execute(create_sql)
