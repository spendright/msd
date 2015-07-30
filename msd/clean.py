# -*- coding: utf-8 -*-
#
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
import re
import unicodedata

from msd.table import TABLES

# matches all whitespace, including non-ascii (e.g. non-breaking space)
WHITESPACE_RE = re.compile(r'\s+', re.U)


BAD_CODEPOINTS = {
    # smart quotes
    0x2018: "'",
    0x2019: "'",
    0x201c: '"',
    0x201d: '"',
    # ligatures
    # from https://en.wikipedia.org/wiki/Typographic_ligature#Ligatures_in_Unicode_.28Latin_alphabets.29  # noqa
    0xfb00: 'ff',
    0xfb01: 'fi',
    0xfb02: 'fl',
    0xfb03: 'ffi',
    0xfb04: 'ffl',
    0xfb06: 'st',
}




def clean(v, translate_bad_chars=True, strip=True, compact_whitespace=True,
          normalize_unicode=True):

    if isinstance(v, bytes):
        raise TypeError

    if not isinstance(v, str):
        return v

    if normalize_unicode:
        v = unicodedata.normalize('NFKD', v)

    if translate_bad_chars:
        v = v.translate(BAD_CODEPOINTS)

    if compact_whitespace:
        v = WHITESPACE_RE.sub(' ', v).strip()

    if strip:
        v = v.strip()

    return v


def clean_row(row, table_name=None):
    """Clean each value in the given row, and remove extra columns."""
    table_def = TABLES.get(table_name, {})
    valid_cols = set(table_def.get('columns', ()))
    clean_kwarg_map = table_def.get('clean_kwargs', {})

    return dict(
        (col_name, clean(value, **clean_kwarg_map.get(col_name, {})))
        for col_name, value in row.items()
        if valid_cols is None or col_name in valid_cols)
