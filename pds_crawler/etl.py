# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
import logging
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import List
from typing import Optional

from .extractor import PDSCatalogsDescription
from .extractor import PdsRecords
from .extractor import PdsRegistry
from .load import Database
from .models import PdsRegistryModel
from .report import CrawlerReport
from .transformer import StacCatalogTransformer
from .transformer import StacRecordsTransformer
from .utils import DocEnum
from .utils import UtilsMonitoring

logger = logging.getLogger(__name__)


class AbstractSourceEnum(DocEnum):
    pass


class AbstractDataEnum(DocEnum):
    pass


class PdsSourceEnum(AbstractSourceEnum):
    COLLECTIONS_INDEX = (
        "ode_collections",
        "Get the georeferenced products",
    )
    COLLECTIONS_INDEX_SAVE = (
        "ode_collections_save",
        "Get and save the PDS collections for the georeferenced products",
    )
    PDS_CATALOGS = (
        "pds_objects",
        "PDS objects describing a catalog (mission, instrument, plateform, ...)",
    )
    PDS_RECORDS = ("ode_records", "Records metadata for a given collection")

    @staticmethod
    def find_enum(name: str):
        """Find enum based on its value

        Args:
            name (str): enum value

        Raises:
            UnknownPFEnum: Unknown value

        Returns:
            PdsSourceEnum: Enum
        """
        result = None
        for pf_name in PdsSourceEnum.__members__:
            val = str(PdsSourceEnum[pf_name].value)
            if val == name:
                result = PdsSourceEnum[pf_name]
                break
        if result is None:
            raise ValueError(f"Unknown enum value for {name}")
        return result


class PdsDataEnum(AbstractDataEnum):
    PDS_CATALOGS = (
        "pds_objects",
        "PDS objects describing a catalog (mission, instrument, plateform, ...)",
    )
    PDS_RECORDS = ("ode_records", "Records metadata for a given collection")

    @staticmethod
    def find_enum(name: str):
        """Find enum based on its value

        Args:
            name (str): enum value

        Raises:
            UnknownPFEnum: Unknown value

        Returns:
            PdsDataEnum: Enum
        """
        result = None
        for pf_name in PdsDataEnum.__members__:
            val = str(PdsDataEnum[pf_name].value)
            if val == name:
                result = PdsDataEnum[pf_name]
                break
        if result is None:
            raise ValueError(f"Unknown enum value for {name}")
        return result


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
        self.__planet: Optional[str] = None

        self.__dataset_id: Optional[str] = None

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

    @property
    def planet(self) -> Optional[str]:
        return self.__planet

    @planet.setter
    def planet(self, name: str):
        self.__planet = name

    @property
    def dataset_id(self) -> Optional[str]:
        return self.__dataset_id

    @dataset_id.setter
    def dataset_id(self, value: str):
        self.__dataset_id = value

    @UtilsMonitoring.timeit
    def extract(self, source: PdsSourceEnum, *args, **kwargs):
        match source:
            case PdsSourceEnum.COLLECTIONS_INDEX:
                (
                    stats,
                    collections_pds,
                ) = self.pds_registry.get_pds_collections(
                    self.planet, self.dataset_id
                )
                for collection in collections_pds:
                    print(collection)
            case PdsSourceEnum.COLLECTIONS_INDEX_SAVE:
                (
                    stats,
                    collections_pds,
                ) = self.pds_registry.get_pds_collections(
                    self.planet, self.dataset_id
                )
                self.pds_registry.cache_pds_collections(collections_pds)
            case PdsSourceEnum.PDS_RECORDS:
                pds_collections: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collections_from_cache(
                    self.planet, self.dataset_id
                )
                self.pds_records.generate_urls_for_all_collections(
                    pds_collections
                )
                self.pds_records.download_pds_records_for_all_collections(
                    pds_collections
                )
            case PdsSourceEnum.PDS_CATALOGS:
                pds_collections: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collections_from_cache(
                    self.planet, self.dataset_id
                )
                self.pds_ode_catalogs.download(pds_collections)
            case _:
                raise NotImplementedError(
                    f"Extraction is not implemented for {source}"
                )

    @UtilsMonitoring.timeit
    def check_extract(self, source: PdsSourceEnum, *args, **kwargs):
        match source:
            case PdsSourceEnum.PDS_RECORDS:
                pds_collections: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collections_from_cache(
                    self.planet, self.dataset_id
                )
                for pds_collection in pds_collections:
                    for (
                        iter
                    ) in self.pds_records.parse_pds_collection_from_cache(
                        pds_collection
                    ):
                        pass
            case PdsSourceEnum.PDS_CATALOGS:
                pds_collections: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collections_from_cache(
                    self.planet, self.dataset_id
                )
                for collection in self.pds_ode_catalogs.get_ode_catalogs(
                    pds_collections
                ):
                    pass
            case _:
                raise NotImplementedError(
                    f"Extraction is not implemented for {source}"
                )

    @UtilsMonitoring.timeit
    def transform(self, data: PdsDataEnum, *args, **kwargs):
        pds_collections: List[
            PdsRegistryModel
        ] = self.pds_registry.load_pds_collections_from_cache(
            self.planet, self.dataset_id
        )
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
                self.stac_records_transformer.load_root_catalog()
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
