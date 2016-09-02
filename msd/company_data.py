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
"""Regexes etc. for parsing company names."""
import re

# always keep this suffix on the company name
UNSTRIPPABLE_COMPANY_TYPES = {
    'LLP',
}

# "The X Co." -- okay to strip
THE_X_CO_RE = re.compile(
    r'^The (?P<company>.*) Co\.$')

# X [&] Co. -- okay to strip
X_CO_RE = re.compile(
    r'^(?P<company>.*?)( \&)? Co\.$'
)

# regexes for stuff that's okay to strip off the company name
COMPANY_NAME_REGEXES = [
    THE_X_CO_RE,
    X_CO_RE,
]

# "The X Company" -- okay for matching, but don't use as short name
THE_X_COMPANY_RE = re.compile(
    r'^The (?P<company>.*) (Co\.|Corporation|Cooperative|Company|Group)$')

# "X Company" -- okay for matching, but don't use as short name
X_COMPANY_RE = re.compile(
    r'^(?P<company>.*?) ('
    r'Brands'
    r'|Co.'
    r'|Company'
    r'|Corporation'
    r'|Enterprises'
    r'|Group'
    r'|Gruppe'
    r'|Holdings?'
    r'|Products'
    r'|Ventures?'
    r')$'
)

# "Groupe X", etc -- basically the non-English version of X Group
GROUPE_X_RE = re.compile(
    r'^(Groupe'
    r'|Grupo'
    r'|Gruppo'
    r') (?P<company>.*)$'
)

# regexes for pulling out company names that are okay for matching
# but shouldn't automatically qualify to be used as a company's canonical name
COMPANY_ALIAS_REGEXES = [
    THE_X_COMPANY_RE,
    X_COMPANY_RE,
    GROUPE_X_RE,
]

# Inc. etc. -- stuff to strip before even doing the above
COMPANY_TYPE_RE = re.compile(
    r'^(?P<company>.*?)(?P<intl1> International)?,? (?P<type>'
    r'A\.?& S\. Klein GmbH \& Co\. KG'
    r'|A/S'
    r'|AB'
    r'|AG'
    r'|AS'
    r'|ASA'
    r'|Ab'
    r'|BV'
    r'|B\.V\.'
    r'|B.V. Nederland'
    r'|C\.V\.'
    r'|Corp\.?'
    r'|GmbH \& C[oO]\. [oO]HG'
    r'|GmbH \& Co\. ?KG\.?'  # handle typo: Lukas Meindl GmbH & Co.KG
    r'|GmbH \& Co\. KGaA'
    r'|GmbH'
    r'|Inc\.?'
    r'|Incorporated'
    r'|International'
    r'|KG\.?'
    r'|Llc'
    r'|LLC'
    r'|LLP'
    r'|LP'
    r'|Limited'
    r'|Llp'
    r'|Pvt\.? Ltd\.?'
    r'|Ltd\.?'
    r'|Ltda\.?'
    r'|nv'
    r'|NV'
    r'|N\.V\.'
    r'|PBC'  # "Public Benefit Corporation" (Delaware benefit corp.)
    r'|PLC'
    r'|P\.C\.'
    r'|Pty\.? Ltd\.?'
    r'|Pty\.?'
    r'|S.\L\.'
    r'|SA'
    r'|SAPI DE CV SOFOM ENR'
    r'|SARL'
    r'|SE'
    r'|S\.A\.?'
    r'|S.A.B. de C.V.'
    r'|S\.A\.U\.'
    r'|S\.R\.L\.'
    r'|S\.p\.A\.'
    r'|Sarl'
    r'|SpA'
    r'|a/s'
    r'|asa'
    r'|b\.v\.'
    r'|gmbh'
    r'|inc\.?'
    r'|plc\.?'
    r')(?P<intl2> International)?$'
)

COMPANY_TYPE_CORRECTIONS = {
    'BV': 'B.V.',
    'Corp': 'Corp.',
    'Incorporated': 'Inc',
    'Llc': 'LLC',
    'Llp': 'LLP',
    'NV': 'N.V.',
    'S.A': 'S.A.',
    'Sarl': 'SARL',
    'SpA': 'S.p.A.',
    'b.v.': 'B.V.',
    'gmbh': 'GmbH',
    'inc': 'Inc',
    'nv': 'N.V.',
}
