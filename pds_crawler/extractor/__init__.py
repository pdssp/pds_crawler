# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Package: extractor

Description:
This package contains a collection of modules to extract information from PDS WS and PDS web site.

Exported components:

* `pds_ode_website`: A module that parses the PDS3 Dataset explorer to get the different catalogs.
* `pds_ode_ws`: A module that provides the metadata for the observations by querying ODE web services.

Usage:
To use this package, you can import and use the exported components as follows:

.. code-block:: python

    from pds_crawler.extractor import PdsRegistry, PdsRecords
    from pds_crawler.models import PdsRegistryModel, PdsRecordModel
    from typing import Tuple, Dict, List

    pds_registry = PdsRegistry(database)

    # Retrieve all the georeferenced collections list
    results: Tuple[Dict[str,str], List[PdsRegistryModel]] = pds_registry.get_pds_collections()


Knowing the collection and one record, it is possible to retrieve extra metadata describing general information.

.. code-block:: python

    from pds_crawler.extractor import PDSCatalogDescription
    from pds_crawler.models import PdsRegistryModel, PdsRecordModel, VolumeModel
    from typing import List

    pds_objects_cat = PDSCatalogDescription(database)

    # Retrieve the URLs of all PDS3 description catalogs (PDS objects)
    pds_objects_cat.load_catalogs_urls(pds_collection)

    # Get the differents URLs of the catalogs
    catalogs_urls: List[str] = pds_objects_cat.catalogs_urls

    # Get the URL of the root directory of the collection
    url: str = pds_objects_cat.url

    # Get volume description catalog
    vol_catalog: VolumeModel = pds_objects_cat.volume_desc_url
"""
from .pds_ode_website import PDSCatalogDescription
from .pds_ode_website import PDSCatalogsDescription
from .pds_ode_ws import PdsRecords
from .pds_ode_ws import PdsRegistry

__all__ = [
    "PdsRegistry",
    "PdsRecords",
    "PDSCatalogDescription",
    "PDSCatalogsDescription",
]
