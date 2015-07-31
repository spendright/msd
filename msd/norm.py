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
"""Normalization of data, mostly strings."""
import re
import unicodedata

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


def clean_string(s, *,
                 compact_whitespace=True,
                 normalize_unicode=True,
                 strip=True,
                 translate_bad_chars=True):
    """Clean messy strings from the outside world."""
    if not isinstance(s, str):
        raise TypeError

    if normalize_unicode:
        s = unicodedata.normalize('NFKD', s)

    if translate_bad_chars:
        s = s.translate(BAD_CODEPOINTS)

    if compact_whitespace:
        s = WHITESPACE_RE.sub(' ', s).strip()

    if strip:
        s = s.strip()

    return s
