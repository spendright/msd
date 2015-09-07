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
from .db import create_table
from .db import insert_row
from .table import TABLES


def create_output_table(output_db, table_name):
    table_def = TABLES[table_name]
    columns = table_def['columns']
    primary_key = table_def['primary_key']
    indexes = table_def.get('indexes', ())

    create_table(output_db, table_name, columns, primary_key)

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

    row = row.copy()

    # delete extra scraper_id column
    if 'scraper_id' in row and 'scraper_id' not in columns:
        del row['scraper_id']

    # make sure primary key cols exists and are non-null
    for k in primary_key:
        if row.get(k) is None:
            if columns[k] == 'text':
                row[k] = ''
            else:
                row[k] = 0

    # make sure is_* fields exist and are either 0 or 1
    for k in sorted(columns):
        if k.startswith('is_'):
            row[k] = int(bool(row.get(k)))

    return row


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


def group_by_keys(items, keyfunc):
    """Given a list of items, returns groups of items, such that if
    any two items share a key returned by keyfunc(item), they are in the
    same group."""

    key_to_group = {}

    for item in items:
        keys = keyfunc(item)

        # strings are also sequences of characters, but that's almost
        # certainly not what we mean
        if isinstance(keys, str):
            raise TypeError(
                '{} is not a valid set of keys (did you mean {}?)'.format(
                    repr(keys), repr([keys])))

        keys = set(keys)


        group = {'keys': keys.copy(), 'items': [item]}

        # merge all matching groups into this one
        ids_seen = set()

        for key in keys:
            group_to_merge = key_to_group.get(key)
            if group_to_merge and id(group_to_merge) not in ids_seen:
                group['keys'].update(group_to_merge['keys'])
                group['items'].extend(group_to_merge['items'])
                ids_seen.add(id(group_to_merge))

        # make all keys point at our new group
        for key in group['keys']:
            key_to_group[key] = group

    # read out all groups
    ids_seen = set()

    for group in key_to_group.values():
        if id(group) not in ids_seen:
            yield group['items']
            ids_seen.add(id(group))
