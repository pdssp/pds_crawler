# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Main program."""
import argparse
import logging
import signal
import sys

from .pdssp_crawler import Crawler
from pds_crawler import __author__
from pds_crawler import __copyright__
from pds_crawler import __description__
from pds_crawler import __version__


class SmartFormatter(argparse.HelpFormatter):
    """Smart formatter for argparse - The lines are split for long text"""

    def _split_lines(self, text, width):
        if text.startswith("R|"):
            return text[2:].splitlines()
        # this is the RawTextHelpFormatter._split_lines
        return argparse.HelpFormatter._split_lines(  # pylint: disable=protected-access
            self, text, width
        )


class SigintHandler:  # pylint: disable=too-few-public-methods
    """Handles the signal"""

    def __init__(self):
        self.SIGINT = False  # pylint: disable=invalid-name

    def signal_handler(self, sig: int, frame):
        """Trap the signal

        Args:
            sig (int): the signal number
            frame: the current stack frame
        """
        # pylint: disable=unused-argument
        logging.error("You pressed Ctrl+C")
        self.SIGINT = True
        sys.exit(2)


def str2bool(string_to_test: str) -> bool:
    """Checks if a given string is a boolean

    Args:
        string_to_test (str): string to test

    Returns:
        bool: True when the string is a boolean otherwise False
    """
    return string_to_test.lower() in ("yes", "true", "True", "t", "1")


def parse_cli() -> argparse.Namespace:
    """Parse command line inputs.

    Returns
    -------
    argparse.Namespace
        Command line options
    """
    parser = argparse.ArgumentParser(
        description=__description__,
        formatter_class=SmartFormatter,
        epilog=__author__ + " - " + __copyright__,
    )
    parser.add_argument(
        "-v", "--version", action="version", version="%(prog)s " + __version__
    )

    parser.add_argument(
        "--level",
        choices=[
            "INFO",
            "DEBUG",
            "WARNING",
            "ERROR",
            "CRITICAL",
            "TRACE",
        ],
        default="INFO",
        help="set Level log (default: %(default)s)",
    )

    subparser = parser.add_subparsers()
    extraction = subparser.add_parser(
        name="extract", description="Data extraction from PDS"
    )
    extraction.add_argument(
        "--type_extract",
        required=True,
        type=str,
        choices=["pds_objects", "ode_collections", "ode_records"],
        help="Extract from a PDS location",
    )
    transform = subparser.add_parser(
        name="transform", description="Data transformation"
    )
    transform.add_argument(
        "--type_stac",
        required=True,
        type=str,
        choices=["catalog", "records"],
        help="Convert to STAC",
    )

    return parser.parse_args()


def run():
    """Main function that instanciates the library."""
    handler = SigintHandler()
    signal.signal(signal.SIGINT, handler.signal_handler)

    try:
        options_cli = parse_cli()

        pds_crawler = Crawler(options_cli=options_cli)
        pds_crawler.run()
        sys.exit(0)
    except Exception as error:  # pylint: disable=broad-except
        logging.exception(error)
        sys.exit(1)


if __name__ == "__main__":
    # execute only if run as a script
    run()
