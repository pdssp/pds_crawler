# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""ETL to index PDS data to pdssp

.. mermaid::

    graph TD
        A[PDS ODE Web Service - collection] --> |JSON| D(Extraction)
        B[PDS ODE Web Service - records] --> |JSON| E(Extraction)
        C[PDS ODE Web Site] --> |REFERENCE_CATALOG, MISSION_CATALOG,<br>PERSONNEL_CATALOG, INSTRUMENT_CATALOG,<br>INSTRUMENT_HOST_CATALOG,DATA_SET_CATALOG,<br>VOL_DESC, DATA_SET_MAP_PROJECTION_CATALOG| F(Extraction)
        E(Extraction) --> |Files| H[Storage File System]
        F(Extraction) --> |Files| M[Storage File System]
        D(Extraction) --> |JSON PdsRegistryModel| I[HDF5]
        I[HDF5] --> |PdsRegistryModel| N[Transform]
        M[Storage File System] --> |PdsRecordsModel, DataSetMapProjectionModel,<br>MissionModel, ReferencesModel,<br>PersonnelsModel, VolumeModel,<br>InstrumentModel, InstrumentHostModel,<br>DataSetModel| L[Transform]
        H[Storage File System] --> |PdsRecordModel| N[Transform]
        I[HDF5] --> |PdsRegistryModel| L[Transform]
        N[Transform] --> |STAC Item, STAC Collection, STAC Catalog| O[STAC repository]
        L[Transform] --> |STAC Collection, STAC Catalog| O[STAC repository]

"""
import logging.config
import os
from logging import NullHandler

from ._version import __author__
from ._version import __author_email__
from ._version import __copyright__
from ._version import __description__
from ._version import __license__
from ._version import __name_soft__
from ._version import __title__
from ._version import __url__
from ._version import __version__
from .custom_logging import LogRecord
from .custom_logging import UtilsLogs

logging.getLogger(__name__).addHandler(NullHandler())

UtilsLogs.add_logging_level("TRACE", 15)
try:
    PATH_TO_CONF = os.path.dirname(os.path.realpath(__file__))
    logging.config.fileConfig(
        os.path.join(PATH_TO_CONF, "logging.conf"),
        disable_existing_loggers=False,
    )
    logging.debug(f"file {os.path.join(PATH_TO_CONF, 'logging.conf')} loaded")
except Exception as exception:  # pylint: disable=broad-except
    logging.warning(f"cannot load logging.conf : {exception}")
logging.setLogRecordFactory(LogRecord)  # pylint: disable=no-member
