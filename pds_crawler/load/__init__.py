# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
# - `pds_archive`: A module that parses the PDS3 catalogs by providing the parser and stores the information
#    in tha appropriate model.
"""
Package: load

Description:
This package contains a collection of modules to store/load information in a database as well as
module to parse PDS3 objects catalogs.

Exported components:
- `database`: A module that stores/loads data from ODE services.
- `PdsParserFactory`: A module that parses any PDS3 catalogs by providing the parser and stores the
information in the appropriate model.
- `StorageCollectionDirectory`: Storage directory to save downloaded files

"""
from .database import Database
from .database import StorageCollectionDirectory
from .pds_objects import PdsParserFactory

__all__ = ["PdsParserFactory", "Database", "StorageCollectionDirectory"]
