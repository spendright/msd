# Copyright 2015 SpendRight, Inc.
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
import msd

try:
    from setuptools import setup
    setup  # quiet "redefinition of unused ..." warning from pyflakes
    # arguments that distutils doesn't understand
    setuptools_kwargs = {
        'install_requires': [
            'Unidecode>=0.04.9',
            'titlecase>=0.7.1',
        ],
        'provides': ['msd'],
        'test_suite': 'test.unit.suite.load_tests',
    }
except ImportError:
    from distutils.core import setup
    setuptools_kwargs = {}

setup(
    author='David Marin',
    author_email='dave@spendright.org',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    description='Merge SpendRight scraper data',
    license='Apache',
    long_description=open('README.rst', encoding='utf_8').read(),
    name='msd',
    packages=[
        'msd',
    ],
    package_data={},
    scripts=['bin/msd'],
    url='http://github.com/spendright/msd',
    version=msd.__version__,
    **setuptools_kwargs
)
