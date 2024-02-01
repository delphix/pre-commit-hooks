#!/usr/bin/env python
#
# Copyright (c) 2023, 2024 by Delphix. All rights reserved.
#
from __future__ import annotations

import argparse
import contextlib
import os
import sys
import typing

import pre_commit.main


@contextlib.contextmanager
def _locked_directory():
    """
    Disable `os.chdir` when in this context.
    """
    old_chdir = os.chdir
    os.chdir = lambda path: ...
    yield
    os.chdir = old_chdir


@contextlib.contextmanager
def _current_directory(directory):
    """
    Change the current working directory for the duration of this context.
    """
    cwd = os.path.abspath(".")
    os.chdir(directory)
    yield
    os.chdir(cwd)


def _create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--directory", dest="directories", action="append")
    parser.add_argument("files", nargs="*")
    return parser


def _sub_files(files: typing.Iterator[str], directory: str) -> typing.Iterator[str]:
    """
    Given a list of files and a directory yield the relative paths of each
    file to that base directory. If the file is not in the directory do not
    yield that file.

    :param files: The file paths
    :param directory: The base directory path
    """
    norm_dir = os.path.normpath(directory)
    for file in files:
        if os.path.commonpath([file, directory]) == norm_dir:
            yield os.path.relpath(file, directory)


def main() -> int:
    args = _create_parser().parse_args()
    result = 0
    for directory in args.directories:
        #
        # Basic configuration validation
        #
        if not os.path.exists(directory):
            raise Exception(f"Directory `{directory}` does not exist.")
        if not os.path.exists(os.path.join(directory, ".pre-commit-config.yaml")):
            raise Exception(
                f"Pre-commit configuration for `{directory}` does not exist."
            )

        #
        # The pre-commit tool calls `os.chdir(<git-repo-root>)` so
        # that all checks are performed at the root of the git
        # repository. We want to avoid this so that paths are relative
        # to the directory that we are testing. As such we cd into the
        # proper directory and lock the directory.
        #
        # This in inherently a hack but the code is simple and easy to
        # change. There is also _no_ other way to do this and the
        # maintainer of pre-commit does _not_ want there to be a way
        # to do this.
        #
        with _current_directory(directory), _locked_directory():
            files = list(_sub_files(args.files, directory))
            if files:
                preface = f"Directory - {directory} "
                print(f"{preface:.<79}", file=sys.stderr)
                cmd = ("run", "--files", *files)
                result += pre_commit.main.main(cmd)
    return result


if __name__ == "__main__":
    sys.exit(main())
