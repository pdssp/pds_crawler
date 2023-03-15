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

* `PdsRegistry`: A module that provides classes to extract the list of PDS3 collections.
* `PdsRecordsWs`: A module that provides classes to extract metadata of the observations and collections by querying ODE web services.
* `PDSCatalogDescription`: A module that provides PDS3 catalogs for a given collection
* `PDSCatalogsDescription`: A module that provides PDS3 catalogs for collections

Usage:
To use this package, you can import and use the exported components as follows:

.. code-block:: python

    from pds_crawler.extractor import PdsRegistry
    from pds_crawler.models import PdsRegistryModel
    from pds_crawler.load import Database
    from typing import Tuple, Dict, List

    # Create a database to store the results
    database = Database('work/database')

    # Create an instance of PdsRegistry to get the collections
    pds_registry = PdsRegistry(database)

    # Retrieve all the georeferenced collections list
    results: Tuple[Dict[str,str], List[PdsRegistryModel]] = pds_registry.get_pds_collections()


By knowing the collection and a record, it is possible to retrieve additional metadata
describing general collection information. This metadata is richer than the metadata
provided in the records of the collection.

Now , we need to download the records. To limit the time to wait, only the first
page is downloaded

.. code-block:: python

    from pds_crawler.extractor import PdsRegistry, PdsRecordsWs
    pds_collection = results[1][60]
    pds_records_ws = PdsRecordsWs(database)
    pds_records_ws.download_pds_records_for_one_collection(pds_collection, 1)

Now, we can retrieve the catalogs that describes the metadata for mission, plateform,
instrument and collection

.. code-block:: python

    from pds_crawler.extractor import PDSCatalogsDescription, PDSCatalogDescription

    # download the catalogs in the storage
    cats = PDSCatalogsDescription(database)
    cats.download([pds_collection])

    # Retrieve the catalogs from the storage
    pds_objects_cat = PDSCatalogDescription(database)
    pds_objects_cat.get_ode_catalogs(pds_collection)

"""
from .pds_ode_website import PDSCatalogDescription
from .pds_ode_website import PDSCatalogsDescription
from .pds_ode_ws import PdsRecordsWs
from .pds_ode_ws import PdsRegistry

__all__ = [
    "PdsRegistry",
    "PdsRecordsWs",
    "PDSCatalogDescription",
    "PDSCatalogsDescription",
]
