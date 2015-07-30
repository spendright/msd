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
"""Table definitions."""
TABLES = {
    'brand': {
        'columns': {
            'brand': 'text',
            'company': 'text',
            'facebook_url': 'text',
            'is_former': 'integer',
            'is_licensed': 'integer',
            'is_prescription': 'integer',
            'logo_url': 'text',
            'tm': 'text',
            'twitter_handle': 'text',
            'url': 'text',
        },
        'primary_key': ['company', 'brand'],
    },
}
