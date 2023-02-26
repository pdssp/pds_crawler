# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""The system architecture consists of several components that work together to crawl
planetary data. The main component can be grouped in two layers:

* persistence layer that includes three storage systems: STAC_Storage, PDS_Storage, and HDF5_Storage, which store data in the File System.
* busisness layer contains the Extractor and Transformer components.

The Extractor component extracts data from the Planetary Data System, which comprises
a web service and a website and sends the retrieved data to both PDS and HDF5 storage.
The Transformer component then transforms the data into the STAC format and stores it
in the STAC_Storage.

The Models component, used by layers, includes four groups of models:

* PDS3 objects - catalogs,
* ODE WS - collections,
* ODE WS - records,
* and STAC.

The diagram below shows the control flow of the components

.. mermaid::

    graph TB
        STAC_Storage ==> FileSystem
        PDS_Storage ==> FileSystem
        HDF5_Storage ==> FileSystem
        Extractor ==> PDS_Storage
        Extractor ==> HDF5_Storage
        Transformer ==> STAC_Storage
        Extractor ==> Planetary_Data_System
        subgraph Planetary_Data_System
            sq01[Website]
            sq02[Web service]
        end
        subgraph PDS_crawler
            subgraph Persistence
                subgraph STAC_Storage
                    sq11[STAC storage]
                    sq12[Strategy]
                end
                subgraph PDS_Storage
                    sq21[PDS storage]
                    sq22[PDS objects]
                end
                subgraph HDF5_Storage
                    sq3[HDF5 storage]
                end
            end
            subgraph FileSystem
                sq3[File System]
            end

            subgraph Business

                subgraph Extractor
                    subgraph ODE_Archive
                        sq71[Website]
                    end
                    subgraph ODE_Web_Service
                        sq81[Collections]
                        sq82[Records]
                    end
                end

                subgraph Transformer
                    subgraph Stac_Transformation
                        sq91[Transformation]
                    end
                end
            end

            subgraph Models
                sq4[PDS3 objects - catalogs]
                sq5[ODE WS - collections]
                sq6[ODE WS - records]
                sq7[STAC]
            end
        end

The diagram below shows the data flow

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

In summary, the architecture consists of three storage systems, an extractor that
retrieves data from various sources, a transformer that converts the data into the
STAC format, and a web service and website component that provides access to catalogs.
Finally, the models component includes four models that represent the different types
of data that the system manages
"""
import logging.config
import os
from logging import debug
from logging import getLogger
from logging import NullHandler
from logging import setLogRecordFactory
from logging import warning

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

getLogger(__name__).addHandler(NullHandler())

try:
    PATH_TO_CONF = os.path.dirname(os.path.realpath(__file__))
    logging.config.fileConfig(
        os.path.join(PATH_TO_CONF, "logging.conf"),
        disable_existing_loggers=False,
    )
    debug(f"file {os.path.join(PATH_TO_CONF, 'logging.conf')} loaded")
except Exception as exception:  # pylint: disable=broad-except
    warning(f"cannot load logging.conf : {exception}")
setLogRecordFactory(LogRecord)  # pylint: disable=no-member
