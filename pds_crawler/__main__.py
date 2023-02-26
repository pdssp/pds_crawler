# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Main program."""
import argparse
import logging
import os
import signal
import sys
from argparse import ArgumentParser

from .etl import PdsDataEnum
from .etl import PdsSourceEnum
from .pds_crawler import Crawler
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


def extraction_parser(subparser):
    extraction = subparser.add_parser(
        name="extract",
        description="Extract information from ODE web service and ODE web site.",
        formatter_class=SmartFormatter,
    )
    extraction.add_argument(
        "--type_extract",
        required=True,
        type=str,
        choices=[
            PdsSourceEnum.COLLECTIONS_INDEX.value,
            PdsSourceEnum.COLLECTIONS_INDEX_SAVE.value,
            PdsSourceEnum.PDS_CATALOGS.value,
            PdsSourceEnum.PDS_RECORDS.value,
        ],
        help=f"""R|Extract an information:
    * {PdsSourceEnum.COLLECTIONS_INDEX.value} : {PdsSourceEnum.COLLECTIONS_INDEX.__doc__}
    * {PdsSourceEnum.COLLECTIONS_INDEX_SAVE.value} : {PdsSourceEnum.COLLECTIONS_INDEX_SAVE.__doc__}
    * {PdsSourceEnum.PDS_CATALOGS.value} : {PdsSourceEnum.PDS_CATALOGS.__doc__}
    * {PdsSourceEnum.PDS_RECORDS.value} : {PdsSourceEnum.PDS_RECORDS.__doc__}
        """,
    )
    extraction.add_argument(
        "--planet",
        required=False,
        type=str,
        help="Extract a planet",
    )
    extraction.add_argument(
        "--dataset_id",
        required=False,
        type=str,
        help="Extract a dataset",
    )
    extraction.add_argument(
        "--nb_workers",
        required=False,
        type=int,
        default=3,
        help="Number of workers to download data (default: %(default)s)",
    )


def check_extraction_parser(subparser):
    check_extraction = subparser.add_parser(
        name="check_extract",
        description="Check extraction from PDS",
        formatter_class=SmartFormatter,
    )
    check_extraction.add_argument(
        "--check",
        required=True,
        type=str,
        choices=[
            PdsSourceEnum.PDS_CATALOGS.value,
            PdsSourceEnum.PDS_RECORDS.value,
        ],
        help=f"""R|Check Extraction of PDS3 objects or PDS records:
    * {PdsSourceEnum.PDS_CATALOGS.value} : {PdsSourceEnum.PDS_CATALOGS.__doc__}
    * {PdsSourceEnum.PDS_RECORDS.value} : {PdsSourceEnum.PDS_RECORDS.__doc__}
        """,
    )

    check_extraction.add_argument(
        "--planet",
        required=False,
        type=str,
        help="Extract a planet",
    )
    check_extraction.add_argument(
        "--dataset_id",
        required=False,
        type=str,
        help="Extract a dataset",
    )


def transform_parser(subparser):
    transform = subparser.add_parser(
        name="transform",
        description="Data transformation",
        formatter_class=SmartFormatter,
    )
    transform.add_argument(
        "--type_stac",
        required=True,
        type=str,
        choices=[
            PdsDataEnum.PDS_CATALOGS.value,
            PdsDataEnum.PDS_RECORDS.value,
        ],
        help=f"""R|Convert to STAC:
    * {PdsDataEnum.PDS_CATALOGS.value} : {PdsDataEnum.PDS_CATALOGS.__doc__}
    * {PdsDataEnum.PDS_RECORDS.value} : {PdsDataEnum.PDS_RECORDS.__doc__}
        """,
    )


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
        ],
        default="INFO",
        help="set Level log (default: %(default)s)",
    )

    parser.add_argument(
        "-d",
        "--database",
        help="Path of the database (default: %(default)s)",
        default=os.path.join("work", "database"),
    )

    subparser = parser.add_subparsers()
    extraction_parser(subparser)
    check_extraction_parser(subparser)
    transform_parser(subparser)

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
