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
import logging
from argparse import ArgumentParser

from msd.output import build_output_db
from msd.scratch import build_scratch_db

DEFAULT_SCRATCH_DB = 'msd-scratch.sqlite'
DEFAULT_OUTPUT_DB = 'msd.sqlite'

log = logging.getLogger('msd.cmd')


def main(args=None):
    opts = parse_args()

    set_up_logging(verbose=opts.verbose, quiet=opts.quiet)

    run(input_db_paths=opts.input_dbs, scratch_db_path=opts.scratch_db,
        output_db_path=opts.output_db, force_rebuild_scratch=opts.force)


def run(*,
        force_rebuild_scratch=False,
        input_db_paths=(),
        output_db_path=DEFAULT_OUTPUT_DB,
        scratch_db_path=DEFAULT_SCRATCH_DB):

    build_scratch_db(scratch_db_path, input_db_paths,
                     force=force_rebuild_scratch)

    build_output_db(scratch_db_path, output_db_path)


def set_up_logging(*, verbose=False, quiet=False):
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARN
    logging.basicConfig(format='%(name)s: %(message)s', level=level)


def parse_args(args=None):
    parser = ArgumentParser()
    parser.add_argument(
        dest='input_dbs', nargs='+',
        help='SQLite databases and/or YAML database dumps to merge')
    parser.add_argument(
        '-v', '--verbose', dest='verbose', default=False, action='store_true',
        help='Enable debug logging')
    parser.add_argument(
        '-q', '--quiet', dest='quiet', default=False, action='store_true',
        help='Turn off info logging')
    parser.add_argument(
        '-f', '--force', dest='force', default=False, action='store_true',
        help='Force rebuild of scratch DB, even if newer than input')
    parser.add_argument(
        '-i', '--scratch', dest='scratch_db',
        default=DEFAULT_SCRATCH_DB,
        help='Path to scratch DB (default: %(default)s)')
    parser.add_argument(
        '-o', '--output', dest='output_db', default=DEFAULT_OUTPUT_DB,
        help='Path to output DB (default: %(default)s)')

    return parser.parse_args(args)



if __name__ == '__main__':
    main()
