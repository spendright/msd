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
"""Supporting data for msd.companies."""
import re

# various misspellings of company names
COMPANY_CORRECTIONS = {
    'Delta Airlines': 'Delta Air Lines',
    'GEPA- The Fairtrade Company': 'GEPA - The Fairtrade Company',
    'Groupo Modelo S.A.B. de C.V.': 'Grupo Modelo S.A.B. de C.V.',
    'Hanesbrands Incorporated': 'Hanesbrands Inc.',
    'Nescafe': 'Nestlé',  # Nescafé is a brand, not a company
    'PUMA AG Rudolf Dassler Sport': 'Puma SE',
    'SAB Miller': 'SABMiller',
    'V.F. Corporation': 'VF Corporation',
    'Wolverine Worldwide': 'Wolverine World Wide',
    'Woolworths Australia': 'Woolworths Limited',
    'Chocoladefabriken Lindt & Sprungli': 'Lindt & Sprüngli AG',
}

# Name changes. May eventually want separate logic for this.
COMPANY_CORRECTIONS.update({
    'Clean Clothes, Inc.': "Maggie's Functional Organics",
    'Limited Brands': 'L Brands',
    'Limited Brands, Inc.': 'L Brands Inc.',
    'Liz Claiborne': 'Kate Spade & Company',
    'Sweet Earth Chocolates': 'Mama Ganache',  # renamed in 2012
    'RIM': 'BlackBerry Limited', # renamed in 2013
    'Research In Motion': 'BlackBerry Limited',
    'Lindt & Sprüngli GmbH': 'Lindt & Sprüngli AG',  # changed corporate form
})

DEFUNCT_COMPANIES = {
    'Armor Holdings',  # acquired by BAE Systems in 2007, integrated
    'Jones Apparel Group',  # acquired by Nine West Inc.
    'The Jones Group',  # another name for Jones Apparel Group
    'News Corporation',  # split into News Corp, 21st Century Fox
}

# sets of names to match companies by
COMPANY_ALIASES = [
    {'LG', 'LGE'},
    {'AEO', 'American Eagle', 'American Eagle Outfitters'},
    {'Merck', 'Schering-Plough'},  # merged into Merck
]

# don't shorten company names to these
BAD_COMPANY_ALIASES = {
    'News',  # e.g. News Corporation, News Corp.
}

# don't use these as display names unless we have no other options
BAD_COMPANY_NAMES = {
    'American Eagle',
    'LGE',
}

# sets of valid names for the same company
COMPANY_NAMES = [
    {'AB Electrolux', 'Electrolux'},
    {'American Eagle Outfitters'},
    {'Anheuser-Busch', 'Anheuser-Busch InBev'},
    {'ASUS', 'ASUSTeK Computer'},
    {'Disney', 'The Walt Disney Company', 'The Walt Disney Co.'},
    {'Gap', 'The Gap'},  # might solve this with "Gap" brand?
    {'GE', 'General Electric'},
    {'HP', 'Hewlett-Packard'},
    {'HTC Electronics', 'HTC'},
    {'Illy', 'illycaffè'},
    {'JetBlue', 'JetBlue Airways'},
    {'Kellogg', "Kellogg's"},  # might solve this with a brand?
    {'L Brands', 'Limited Brands'},
    {'Lindt', 'Lindt & Sprüngli'},
    {'Lidl', 'Lidl Stiftung'},
    {'LG', 'LG Electronics'},
    {'New Look', 'New Look Retailers'},
    {'Philips', 'Royal Philips', 'Royal Philips Electronics'},
    {'PVH', 'Phillips Van Heusen'},
    {'Rivers Australia', 'Rivers (Australia) Pty Ltd'},
    # technically, Wells Fargo Bank, N.A. is a subsidiary of Wells Fargo
    # the multinational. Not worrying about this now and I don't think this is
    # what they meant anyway.
    {'Wells Fargo', 'Wells Fargo Bank'},
    {'Whole Foods', 'Whole Foods Market'},
    {'Wibra', 'Wibra Supermarkt'},
]

# always keep this suffix on the company name
UNSTRIPPABLE_COMPANY_TYPES = {
    'LLP',
}

# don't use the regexes below to shorten these company names
UNSTRIPPABLE_COMPANIES = {
    'Globe International',
    'Woolworths Limited',
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
    r'|Corp.'
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
