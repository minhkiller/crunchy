#!/usr/bin/env python

import filecmp
import os
import os.path as paths
import shutil
import sys
from pprint import pformat
from subprocess import call
from optparse import OptionParser

# Usage sub-paragraph.
BLURB = """I run 2to3 on a source directory and write the output files
to a destination directory. The other way to run me is to pass a
source file and a destination file. I handle doctest .rst files in
addition to Python files. I avoid recompilation wherever possible by
comparing file contents first. I require Python 3.1's 2to3; 2.6's 2to3
is known to improperly convert Crunchy's source."""

# Argument for subprocess.call().
_2TO3 = ['2to3', '-w']

class Error(SystemExit):
    """A SystemExit with error strings included."""

    _2to3 = \
        'Called 2to3 with {args} and it exited with {ret}'

    mismatch = \
        'Both arguments have to be directories, or both have to be files'

    def __init__(self, key, **kw):
        """Prints a specified error to standard error then constructs
        a SystemExit instance with status code 1."""

        text = getattr(Error, key).format(**kw)
        sys.stderr.write('build_python3.py: error: {}\n'.format(text))
        # Status code is always one.
        super().__init__(1)

def copy(src, dst):
    """Copies file at src to path at dst and logs it to stdout. Will
    make the dst directory if necessary."""

    # normpath calling is a must. makedirs does not like os.pardir
    # ('..') in paths.
    dirname = paths.normpath(paths.dirname(dst))
    if not paths.exists(dirname):
        print('Making {}'.format(dirname))
        os.makedirs(dirname)

    print('Copying {} to {}'.format(src, dst))
    shutil.copyfile(src, dst)

def remove(victim):
    """Removes file and logs it to stdout."""

    print('Removing {}'.format(victim))
    os.remove(victim)

def main_copy(src, dst, opts=[]):
    """Copies src to dst and then runs the mutating 2to3 on dst in a
    subprocess. Raises an Error if 2to3 fails."""

    copy(src, dst)

    # Call 2to3.
    args = _2TO3 + opts + [dst]
    ret  = call(args)
    if not ret == 0:
        raise Error('_2to3', args=args, ret=ret)

def parallel_walk(src, dst):
    """Walks both directories. Yields the paths of files in the source
    directory and the expected corresponding path in the
    destination."""
    for root, dirs, files in os.walk(src):
        if '.svn' in dirs:
            dirs.remove('.svn')

        for file in files:
            a = paths.join(root, file)
            b = a.replace(src, dst, 1)
            yield a, b

def main_deep_copy(src, dst, force=False):
    """Walks the src directory and copies each file to dst before
    running 2to3 on it. Skips unnecessary files. Raises an Error if
    2to3 fails. A force argument of True skips the logic that tries to
    avoid recompilation."""

    for a, b in parallel_walk(src, dst):
        root, ext = paths.splitext(a)

        if ext == '.pyc':
            # Unnecessary, but just to be sure: Clean up .pyc files in
            # case it conflicts with newer .py files.
            if paths.exists(b):
                os.remove(b)

        elif ext in ('.py', '.rst'):
            # os.path.join thinks "b" is a directory and does the
            # wrong thing here.
            bak = b + '.bak'

            if paths.exists(b) and not force:
                # Skip if .bak exists and is a match, indicating the
                # source file has not changed.
                if paths.exists(bak):
                    if filecmp.cmp(a, bak):
                        print('Skipping {}: unchanged'.format(a))
                        continue

                # If no .bak file exists, that means 2to3 skipped the
                # file.
                else:
                    if filecmp.cmp(a, b):
                        print('Skipping {}: unchanged'.format(a))
                        continue

            if ext == '.py':
                main_copy(a, b)
            else:
                main_copy(a, b, opts=['-d'])

        else:
            if not paths.exists(b) or not filecmp.cmp(a, b):
                copy(a, b)

def main():
    """Parses command-line arguments and raises the appropriate
    SystemExit exception."""

    usage  = "usage: %prog [-f] src dest\n\n" + BLURB
    parser = OptionParser(usage=usage)
    parser.add_option('-f', '--force', dest='force',
                      help='Force recompilation',
                      action='store_true')

    options, args = parser.parse_args()

    # {filename} and {dest} were passed.
    if not len(args) == 2:
        parser.print_help()
        raise SystemExit(1)

    src, dst = args
    if paths.isdir(src) and paths.isdir(dst):
        main_deep_copy(src, dst, force=options.force)
    elif paths.isfile(src) and paths.isfile(dst):
        main_copy(src, dst)
    else:
        raise Error('mismatch')

    raise SystemExit()

if __name__ == '__main__':
    main()
