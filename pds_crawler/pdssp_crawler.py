# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""This module contains the library."""
import logging
from typing import Dict
from typing import List

from ._version import __name_soft__
from .etl import PdsDataEnum
from .etl import PdsSourceEnum
from .etl import StacETL

logger = logging.getLogger(__name__)


class Crawler:
    """The library"""

    def __init__(self, options_cli, *args, **kwargs):
        self.__options_cli = options_cli

    @property
    def options_cli(self):
        return self.__options_cli

    def run(self):
        database_name = self.options_cli.database
        logger.info(f"Using {database_name} as database")
        etl = StacETL(database_name)

        if hasattr(self.options_cli, "type_stac"):
            match self.options_cli.type_stac:
                case "catalog":
                    etl.transform(data=PdsDataEnum.PDS_CATALOGS)
                case "records":
                    etl.transform(data=PdsDataEnum.PDS_RECORDS)
                case _:
                    raise TypeError(
                        f"Unexpected option {self.options_cli.type_stac} for typ_stac"
                    )

        if hasattr(self.options_cli, "type_extract"):
            match self.options_cli.type_extract:
                case "ode_collections":
                    etl.extract(source=PdsSourceEnum.COLLECTIONS_INDEX)
                case "pds_objects":
                    etl.extract(source=PdsSourceEnum.PDS_CATALOGS)
                case "ode_records":
                    etl.extract(source=PdsSourceEnum.PDS_RECORDS)
                case _:
                    raise TypeError(
                        f"Unexpected option {self.options_cli.type_extract} for type_extract"
                    )
