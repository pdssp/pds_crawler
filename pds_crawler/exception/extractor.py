# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
from .error import CrawlerError
from .error import ModelError


class PdsCollectionAttributeError(ModelError):
    """Missing a mandatatory attribute in PdsCollection."""


class PdsRecordAttributeError(ModelError):
    """Missing a mandatatory attribute in PdsRecord."""


class NoFileExistInFolder(CrawlerError):
    """No content in PDS directory"""


class PdsCatalogDescriptionError(CrawlerError):
    """PDS error"""


class PlanetNotFound(CrawlerError):
    """Planet not found"""


class DateConversionError(CrawlerError):
    """Problem when converting a date"""


class ParserTimeOutError(CrawlerError):
    """Timeout when parsing with Lark"""
