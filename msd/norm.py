# -*- coding: utf-8 -*-
#
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
"""Normalization of data, mostly strings."""
import re
import unicodedata

from titlecase import titlecase
from unidecode import unidecode

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


def clean_string(s):
    """Clean messy strings from the outside world."""
    if not isinstance(s, str):
        raise TypeError

    # see issue #32 for why we use NFC
    s = unicodedata.normalize('NFC', s)
    s = s.translate(BAD_CODEPOINTS)
    s = simplify_whitespace(s)

    return s


def simplify_whitespace(s):
    """Strip s, and use only single spaces within s."""
    return WHITESPACE_RE.sub(' ', s.strip())


def to_title_case(s):
    """Like titlecase.titlecase(), but treat hyphens as spaces."""
    return ''.join(
        '-' if s[i] == '-' else c
        for i, c in enumerate(titlecase(s.replace('-', ' '))))


def norm(s):
    """Remove accents and convert to lowercase."""
    return unidecode(s).lower()


def smunch(s):
    """Like norm(), except we remove whitespace too."""
    return WHITESPACE_RE.sub('', norm(s))
