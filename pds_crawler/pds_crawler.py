# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""This module contains the library."""
import logging
from typing import cast
from typing import List

from ._version import __name_soft__
from .etl import CheckUpdateEnum
from .etl import PdsDataEnum
from .etl import PdsSourceEnum
from .etl import StacETL

logging.basicConfig(level=logging.CRITICAL)

logger = logging.getLogger(__name__)


class Crawler:
    """The library"""

    def __init__(self, options_cli, *args, **kwargs):
        """
        Initializes a Crawler object.

        Args:
            options_cli: An object with attributes that correspond to the command
                         line options passed to the program.
            args: Additional positional arguments.
            kwargs: Additional keyword arguments.
        """
        self.__options_cli = options_cli
        Crawler._parse_level(options_cli.level)
        # logging.getLogger().setLevel(level="CRITICAL")

    @property
    def options_cli(self):
        """
        The command line options passed to the program.

        Returns:
            An object with attributes that correspond to the command line options.
        """
        return self.__options_cli

    @staticmethod
    def _parse_level(level: str):
        """Parse level name and set the rigt level for the logger.
        If the level is not known, the INFO level is set

        Args:
            level (str): level name
        """
        pds_crawler_logger = logging.getLogger("pds_crawler")
        if level == "NOTSET":
            pds_crawler_logger.setLevel(logging.NOTSET)
        elif level == "INFO":
            pds_crawler_logger.setLevel(logging.INFO)
        elif level == "DEBUG":
            pds_crawler_logger.setLevel(logging.DEBUG)
        elif level == "WARNING":
            pds_crawler_logger.setLevel(logging.WARNING)
        elif level == "ERROR":
            pds_crawler_logger.setLevel(logging.ERROR)
        elif level == "CRITICAL":
            pds_crawler_logger.setLevel(logging.CRITICAL)
        else:
            pds_crawler_logger.warning(
                f"Unknown level name : {level} - setting level to INFO"
            )
            logger.setLevel(logging.INFO)

    def run(self):
        """
        Runs the crawler.
        """
        database_name = self.options_cli.database
        logger.info(f"Using {database_name} as database")
        etl = StacETL(database_name)
        etl.progress_bar = self.options_cli.progress_bar

        if hasattr(self.options_cli, "type_stac"):
            if self.options_cli.body:
                etl.body = self.options_cli.body

            if self.options_cli.dataset_id:
                etl.dataset_id = self.options_cli.dataset_id

            if self.options_cli.parser_timeout:
                etl.parser_timeout = self.options_cli.parser_timeout

            enum = PdsDataEnum.find_enum(self.options_cli.type_stac)
            etl.transform(data=enum)

        if hasattr(self.options_cli, "type_extract"):
            if self.options_cli.body:
                etl.body = self.options_cli.body

            if self.options_cli.dataset_id:
                etl.dataset_id = self.options_cli.dataset_id

            etl.nb_workers = int(self.options_cli.nb_workers)
            etl.nb_records_per_page = int(self.options_cli.nb_records_per_page)

            enum = PdsSourceEnum.find_enum(self.options_cli.type_extract)
            etl.extract(source=enum)

        if hasattr(self.options_cli, "check"):
            if self.options_cli.body:
                etl.body = self.options_cli.body

            if self.options_cli.dataset_id:
                etl.dataset_id = self.options_cli.dataset_id

            enum = CheckUpdateEnum.find_enum(self.options_cli.check)
            etl.check_update(source=enum)
