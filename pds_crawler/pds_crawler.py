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
from .etl import PdsDataEnum
from .etl import PdsSourceEnum
from .etl import StacETL
from .models import PdsRegistryModel

logging.basicConfig(level=logging.CRITICAL)

logger = logging.getLogger(__name__)


class Crawler:
    """The library"""

    def __init__(self, options_cli, *args, **kwargs):
        self.__options_cli = options_cli
        Crawler._parse_level(options_cli.level)
        # logging.getLogger().setLevel(level="CRITICAL")

    @property
    def options_cli(self):
        return self.__options_cli

    @staticmethod
    def _parse_level(level: str):
        """Parse level name and set the rigt level for the logger.
        If the level is not known, the INFO level is set

        Args:
            level (str): level name
        """
        pds_crawler_logger = logging.getLogger("pds_crawler")
        if level == "INFO":
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
                "Unknown level name : %s - setting level to INFO", level
            )
            logger.setLevel(logging.INFO)

    def run(self):
        database_name = self.options_cli.database
        logger.info(f"Using {database_name} as database")
        etl = StacETL(database_name)

        if hasattr(self.options_cli, "type_stac"):
            enum = PdsDataEnum.find_enum(self.options_cli.type_stac)
            etl.transform(data=enum)

        if hasattr(self.options_cli, "type_extract"):
            if self.options_cli.planet:
                etl.planet = self.options_cli.planet

            if self.options_cli.dataset_id:
                etl.dataset_id = self.options_cli.dataset_id

            if self.options_cli.nb_workers:
                etl.pds_records.nb_workers = int(self.options_cli.nb_workers)

            enum = PdsSourceEnum.find_enum(self.options_cli.type_extract)
            etl.extract(source=enum)

        if hasattr(self.options_cli, "check"):
            if self.options_cli.planet:
                etl.planet = self.options_cli.planet

            if self.options_cli.dataset_id:
                etl.dataset_id = self.options_cli.dataset_id

            match self.options_cli.check:
                case PdsDataEnum.PDS_CATALOGS.value:
                    etl.check_extract(source=PdsSourceEnum.PDS_CATALOGS)
                case PdsDataEnum.PDS_RECORDS.value:
                    etl.check_extract(source=PdsSourceEnum.PDS_RECORDS)
                case _:
                    raise TypeError(
                        f"Unexpected option {self.options_cli.type_extract} for type_extract"
                    )
