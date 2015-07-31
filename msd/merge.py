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
from .db import create_index
from .db import insert_row
from .table import TABLES


def create_output_table(output_db, table_name):
    table_def = TABLES[table_name]
    columns = table_def['columns']
    primary_key = table_def['primary_key']
    indexes = table_def.get('indexes', ())

    create_sql = 'CREATE TABLE `{}` ({}, PRIMARY KEY ({}))'.format(
        table_name,
        ', '.join('`{}` {}'.format(col_name, col_type)
                  for col_name, col_type in sorted(columns.items())),
        ', '.join('`{}`'.format(pk_col) for pk_col in primary_key))
    output_db.execute(create_sql)

    for index_cols in indexes:
        create_index(output_db, table_name, index_cols)


def clean_output_row(row, table_name):
    """Clean row for output to the output DB.

    Currently handles:
    * removing extra 'scraper_id' field
    * coercing is_* fields to 0 or 1
    """
    table_def = TABLES[table_name]
    columns = table_def['columns']
    primary_key = table_def.get('primary_key', ())

    cleaned = {}

    for k, v in sorted(row.items()):
        if k == 'scraper_id' and 'scraper_id' not in columns:
            continue

        # coerce is_* fields to 0 or 1
        if k.startswith('is_'):
            v = int(bool(v))

        # don't allow null in primary key
        if k in primary_key and v is None:
            if columns[k] == 'text':
                v = ''
            else:
                v = 0

        cleaned[k] = v

    return cleaned


def output_row(output_db, table_name, row):
    """Clean row and output it to output_db."""
    row = clean_output_row(row, table_name)
    insert_row(output_db, table_name, row)


def merge_dicts(ds):
    """Merge a sequence of dictionaries."""
    result = {}

    for d in ds:
        for k, v in d.items():
            if k not in result:
                if hasattr(v, 'copy'):
                    result[k] = v.copy()
                else:
                    result[k] = v
            else:
                if hasattr(result[k], 'update'):
                    result[k].update(v)
                elif hasattr(result[k], 'extend'):
                    result[k].extend(v)
                elif result[k] is None:
                    result[k] = v
                elif result[k] == '' and v != '':
                    result[k] = v

    return result
