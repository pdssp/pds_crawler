# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
import logging
import os
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import Iterator
from typing import List

import pystac

from .extractor import PDSCatalogsDescription
from .extractor import PdsRecords
from .extractor import PdsRegistry
from .load import Database
from .models import PdsRecordModel
from .models import PdsRecordsModel
from .models import PdsRegistryModel
from .report import CrawlerReport
from .transformer import StacCatalogTransformer
from .transformer import StacRecordsTransformer
from .utils import DocEnum

logger = logging.getLogger(__name__)


class AbstractSourceEnum(DocEnum):
    pass


class AbstractDataEnum(DocEnum):
    pass


class PdsSourceEnum(AbstractSourceEnum):
    COLLECTIONS_INDEX = (
        "collections",
        "Names of the PDS collection for the georeferenced products",
    )
    PDS_CATALOGS = (
        "catalogs",
        "PDS objects describing a catalog (mission, instrument, plateform, ...)",
    )
    PDS_RECORDS = ("records", "Records metadata for a given collection")


class PdsDataEnum(AbstractDataEnum):
    PDS_CATALOGS = (
        "catalogs",
        "PDS objects describing a catalog (mission, instrument, plateform, ...)",
    )
    PDS_RECORDS = ("records", "Records metadata for a given collection")


class ETL(ABC):
    @abstractmethod
    def extract(self, source: AbstractSourceEnum, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def transform(self, data: AbstractDataEnum, *args, **kwargs):
        raise NotImplementedError()

    @abstractmethod
    def load(self, data: PdsDataEnum, target: Any, *args, **kwargs):
        raise NotImplementedError()


class StacETL(ETL):
    def __init__(self, full_path_database_name: str) -> None:
        db = Database(full_path_database_name)
        self.__report = CrawlerReport(db)
        self.__pds_registry = PdsRegistry(db, report=self.__report)
        self.__pds_records = PdsRecords(db, report=self.__report)
        self.__pds_ode_catalogs = PDSCatalogsDescription(
            db, report=self.__report
        )
        self.__stac_catalog_transformer = StacCatalogTransformer(
            db, report=self.__report
        )
        self.__stac_records_transformer = StacRecordsTransformer(
            db, report=self.__report
        )

    @property
    def report(self) -> CrawlerReport:
        return self.__report

    @property
    def pds_registry(self) -> PdsRegistry:
        return self.__pds_registry

    @property
    def pds_records(self) -> PdsRecords:
        return self.__pds_records

    @property
    def pds_ode_catalogs(self) -> PDSCatalogsDescription:
        return self.__pds_ode_catalogs

    @property
    def stac_catalog_transformer(self) -> StacCatalogTransformer:
        return self.__stac_catalog_transformer

    @property
    def stac_records_transformer(self) -> StacRecordsTransformer:
        return self.__stac_records_transformer

    def extract(self, source: PdsSourceEnum, *args, **kwargs):
        match source:
            case PdsSourceEnum.COLLECTIONS_INDEX:
                (
                    stats,
                    collections_pds,
                ) = self.pds_registry.get_collections_pds()
                self.pds_registry.cache_collections_pds(collections_pds)
            case PdsSourceEnum.PDS_RECORDS:
                pds_collections: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collection_from_cache()
                self.pds_records.generate_urls_collections(pds_collections)
                self.pds_records.download_pds_collections(pds_collections)
            case PdsSourceEnum.PDS_CATALOGS:
                pds_collections: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collection_from_cache()
                self.pds_ode_catalogs.download(pds_collections)
            case _:
                raise NotImplementedError(
                    f"Extraction is not implemented for {source}"
                )

    def transform(self, data: PdsDataEnum, *args, **kwargs):
        pds_collections: List[
            PdsRegistryModel
        ] = self.pds_registry.load_pds_collection_from_cache()
        match data:
            case PdsDataEnum.PDS_CATALOGS:
                self.report.name = PdsDataEnum.PDS_CATALOGS.name
                self.report.start_report()
                self.stac_catalog_transformer.init()
                self.stac_catalog_transformer.to_stac(
                    self.pds_ode_catalogs, pds_collections
                )
                self.stac_catalog_transformer.save()
                self.report.close_report()
            case PdsDataEnum.PDS_RECORDS:
                self.report.name = PdsDataEnum.PDS_RECORDS.name
                self.report.start_report()
                self.stac_records_transformer.init()
                self.stac_records_transformer.read_root_catalog()
                self.stac_records_transformer.to_stac(
                    self.pds_records, pds_collections
                )
                self.stac_records_transformer.save()
                self.report.close_report()
            case _:
                raise NotImplementedError(
                    f"Transformation is not implemented for {data}"
                )

    def load(self, data: PdsDataEnum, target: str, *args, **kwargs):
        pass
