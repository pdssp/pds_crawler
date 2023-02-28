# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Package: transformer

Description:
This package contains a collection of modules to transform extracted information to STAC.

Exported components:

* `StacCatalogTransformer`: A module that converts the extracted PDS catalogs to STAC.
* `StacRecordsTransformer`: A module that converts the extracted responses from PDsRecordsWs to STAC.

Usage:
To use this package, you can import and use the exported components as follows:

.. code-block:: python

   from pds_crawler.extractor import PDSCatalogsDescription
   from pds_crawler.transformer import StacCatalogTransformer
   cats = PDSCatalogsDescription(database)
   cats.download([pds_collection])
   transf = StacCatalogTransformer(database)
   transf.to_stac(cats, [pds_collection])
   transf.save()

"""
from .pds_to_stac import StacCatalogTransformer
from .pds_to_stac import StacRecordsTransformer

__all__ = ["StacCatalogTransformer", "StacRecordsTransformer"]
