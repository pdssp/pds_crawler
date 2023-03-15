# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Package: models

Description:
This package contains the collection of models that the pds_crawler uses.

Exported components:

- `PdsRegistryModel`: Model of the collections from the ODE webservice.
- `PdsRecordsModel` : Model of the records from the ODE webservice
- `PdsRecordModel` : Model for one record from the ODE webservice
- `DataSetModel` : PDS3 model for dataset
- `InstrumentModel` : PDS3 model for the instrument
- `InstrumentHostModel` : PDS3 model for the plateform
- `MissionModel` : PDS3 model for mission
- `PersonnelsModel` : PDS3 model for the point of contacts
- `ReferencesModel` : PDS3 model for the citations
- `VolumeModel` : PDS3 model for the general description of the volume
- `DataSetMapProjectionModel` : PDS3 model for the dataset projection
- `CatalogModel` : PDS3 model for catalog
- `PdsspModel` : PDSSP model
- `Labo` : Labo mode
"""
from .ode_ws_models import PdsRecordModel
from .ode_ws_models import PdsRecordsModel
from .ode_ws_models import PdsRegistryModel
from .pds_models import CatalogModel
from .pds_models import DataSetMapProjectionModel
from .pds_models import DataSetModel
from .pds_models import InstrumentHostModel
from .pds_models import InstrumentModel
from .pds_models import Labo
from .pds_models import MissionModel
from .pds_models import PersonnelsModel
from .pds_models import ReferencesModel
from .pds_models import VolumeModel
from .pdssp_models import PdsspModel

__all__ = [
    "PdsRegistryModel",
    "PdsRecordsModel",
    "PdsRecordModel",
    "DataSetModel",
    "InstrumentModel",
    "InstrumentHostModel",
    "MissionModel",
    "PersonnelsModel",
    "ReferencesModel",
    "VolumeModel",
    "DataSetMapProjectionModel",
    "CatalogModel",
    "PdsspModel",
    "Labo",
]
