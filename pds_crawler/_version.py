# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Project metadata."""
from pkg_resources import DistributionNotFound
from pkg_resources import get_distribution

__name_soft__ = "pds_crawler"
try:
    __version__ = get_distribution(__name_soft__).version
except DistributionNotFound:
    __version__ = "0.0.0"
__title__ = "pds-crawler"
__description__ = """Crawl and extract PDS planetary data from various sources,
including a web service and a website, transform the data into the SpatioTemporal Asset
Catalog (STAC) format."""
__url__ = "https://github.com/pdssp/pds_crawler"
__author__ = "Jean-Christophe Malapert"
__author_email__ = "jean-christophe.malapert@cnes.fr"
__license__ = "GNU Lesser General Public License v3"
__copyright__ = (
    "2023, CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)"
)
