# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Package: load

Description:
This package contains a collection of modules to store/load information in a database as well as
module to parse PDS3 objects catalogs.

Exported components:

- `database`: A module that stores/loads data from ODE services.
- `PdsParserFactory`: A module that parses any PDS3 catalogs by providing the parser and stores the information in the appropriate model.
- `PdsStorage`: General storage to save downloaded files
- `PdsCollectionStorage`: Storage directory to save downloaded files
- `Hdf5Storage`: HDF5


"""
from .database import Database
from .database import Hdf5Storage
from .database import PdsCollectionStorage
from .database import PdsStorage
from .pds_objects_parser import PdsParserFactory

__all__ = [
    "PdsParserFactory",
    "Database",
    "PdsStorage",
    "PdsCollectionStorage",
    "Hdf5Storage",
]
