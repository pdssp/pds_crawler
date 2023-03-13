# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Provides a ETL API.

.. code:: python

    from pds_crawler.etl import PdsSourceEnum, PdsDataEnum, StacETL
    etl = StacETL("work/database")
    etl.extract(PdsSourceEnum.COLLECTIONS_INDEX)


"""
import logging
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import cast
from typing import List
from typing import Optional
from typing import Tuple

from pystac import Catalog
from pystac import Collection

from .extractor import PDSCatalogsDescription
from .extractor import PdsRecordsWs
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


class CheckUpdateEnum(AbstractSourceEnum):
    CHECK_PDS = (
        "pds",
        "Check updates at PDS",
    )
    CHECK_CACHE = (
        "cache",
        "Check if some collections in cache are not transformed",
    )

    @staticmethod
    def find_enum(name: str):
        """Find enum based on its value

        Args:
            name (str): enum value

        Raises:
            ValuError: Unknown value

        Returns:
            CheckUpdateEnum: Enum
        """
        result = None
        for pf_name in CheckUpdateEnum.__members__:
            val = str(CheckUpdateEnum[pf_name].value)
            if val == name:
                result = CheckUpdateEnum[pf_name]
                break
        if result is None:
            raise ValueError(f"Unknown enum value for {name}")
        return result


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
    """ETL to extract and transform PDS information to STAC"""

    def __init__(self, full_path_database_name: str) -> None:
        db = Database(full_path_database_name)
        self.__report = CrawlerReport(db)
        self.__pds_registry = PdsRegistry(db, report=self.__report)
        self.__pds_records = PdsRecordsWs(db, report=self.__report)
        self.__pds_ode_catalogs = PDSCatalogsDescription(
            db, report=self.__report
        )
        self.__stac_catalog_transformer = StacCatalogTransformer(
            db, report=self.__report
        )
        self.__stac_records_transformer = StacRecordsTransformer(
            db, report=self.__report
        )
        self.__body: Optional[str] = None

        self.__dataset_id: Optional[str] = None
        self.__nb_workers: int = 3
        self.__time_sleep: int = 1
        self.__progress_bar: bool = True
        self.__is_sample: bool = False
        self.__nb_records_per_page: int = 5000
        self.__parser_timeout: int = 60

    @property
    def nb_records_per_page(self) -> int:
        return self.__nb_records_per_page

    @nb_records_per_page.setter
    def nb_records_per_page(self, value: int):
        self.__nb_records_per_page = value

    @property
    def report(self) -> CrawlerReport:
        return self.__report

    @report.setter
    def report(self, value: CrawlerReport):
        self.__report = value

    @property
    def pds_registry(self) -> PdsRegistry:
        return self.__pds_registry

    @property
    def pds_records(self) -> PdsRecordsWs:
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
    def body(self) -> Optional[str]:
        return self.__body

    @body.setter
    def body(self, name: str):
        self.__body = name

    @property
    def dataset_id(self) -> Optional[str]:
        return self.__dataset_id

    @dataset_id.setter
    def dataset_id(self, value: str):
        self.__dataset_id = value

    @property
    def nb_workers(self) -> int:
        return self.__nb_workers

    @nb_workers.setter
    def nb_workers(self, value: int):
        self.__nb_workers = value

    @property
    def time_sleep(self) -> int:
        return self.__time_sleep

    @time_sleep.setter
    def time_sleep(self, value: int):
        self.__time_sleep = value

    @property
    def progress_bar(self) -> bool:
        return self.__progress_bar

    @progress_bar.setter
    def progress_bar(self, value: bool):
        self.__progress_bar = value

    @property
    def is_sample(self) -> bool:
        return self.__is_sample

    @is_sample.setter
    def is_sample(self, value: bool):
        self.__is_sample = value

    @property
    def parser_timeout(self) -> int:
        return self.__parser_timeout

    @parser_timeout.setter
    def parser_timeout(self, value: int):
        self.__parser_timeout = value

    @UtilsMonitoring.timeit
    def extract(self, source: PdsSourceEnum, *args, **kwargs):
        """Extract the PDS information.

        It exists different types of extraction:

        * COLLECTIONS_INDEX : query the PDS to get the georefereced collections
        * COLLECTIONS_INDEX_SAVE : like COLLECTIONS_INDEX but save the result in cache
        * PDS_RECORDS : Load the PDS collections from cache, build and cache all the URLs to get all pages of the PdsRecordsWs and download all pages
        * PDS_CATALOGS : Load the PDS collections from cache, and download the PDS3 objects

        Args:
            source (PdsSourceEnum): Type of extraction

        Raises:
            NotImplementedError: Extraction type is not implemented
        """
        match source:
            case PdsSourceEnum.COLLECTIONS_INDEX:
                (
                    stats,
                    collections_pds,
                ) = self.pds_registry.get_pds_collections(
                    self.body, self.dataset_id
                )
                for collection in collections_pds:
                    print(collection)
            case PdsSourceEnum.COLLECTIONS_INDEX_SAVE:
                (
                    stats,
                    collections_pds,
                ) = self.pds_registry.get_pds_collections(
                    self.body, self.dataset_id
                )
                self.pds_registry.cache_pds_collections(collections_pds)
            case PdsSourceEnum.PDS_RECORDS:
                pds_collections: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collections_from_cache(
                    self.body, self.dataset_id
                )
                self.pds_records.generate_urls_for_all_collections(
                    pds_collections=pds_collections,
                    limit=self.nb_records_per_page,
                )
                limit: Optional[int] = 1 if self.is_sample else None
                self.pds_records.download_pds_records_for_all_collections(
                    pds_collections=pds_collections,
                    progress_bar=self.progress_bar,
                    limit=limit,
                )
            case PdsSourceEnum.PDS_CATALOGS:
                pds_collections: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collections_from_cache(
                    self.body, self.dataset_id
                )
                self.pds_ode_catalogs.download(
                    pds_collections=pds_collections,
                    nb_workers=self.nb_workers,
                    time_sleep=self.time_sleep,
                    progress_bar=self.progress_bar,
                )
            case _:
                raise NotImplementedError(
                    f"Extraction is not implemented for {source}"
                )

    def _check_collections_to_ingest(
        self, cached_pds_collections: List[PdsRegistryModel]
    ) -> int:
        db: Database = self.stac_records_transformer.database
        root_stac_catalog: Catalog = cast(
            Catalog, db.stac_storage.root_catalog
        )
        nb_to_ingest: int = 0
        for pds_collection in cached_pds_collections:
            coll = cast(
                Collection,
                root_stac_catalog.get_child(
                    pds_collection.get_collection_id(), recursive=True
                ),
            )
            if coll is None:
                nb_to_ingest += 1
                logger.info(f"{pds_collection} was not ingested")
        return nb_to_ingest

    def _check_updates_from_PDS(
        self,
        pds_collections: List[PdsRegistryModel],
        pds_collections_cache: List[PdsRegistryModel],
    ) -> int:
        nb_to_update: int = 0
        for pds_collection_cache in pds_collections_cache:
            try:
                pds_collections.index(pds_collection_cache)
            except ValueError:
                nb_to_update += 1
                logger.info(f"{pds_collections_cache} has been updated at PDS")
        return nb_to_update

    def check_collections_to_ingest_from_pds(
        self,
        pds_collections: List[PdsRegistryModel],
        pds_collections_cache: List[PdsRegistryModel],
    ) -> Tuple[int, int]:
        nb_to_ingest: int = 0
        nb_records: int = 0
        for pds_collection in pds_collections:
            try:
                pds_collections_cache.index(pds_collection)
            except ValueError:
                nb_records += pds_collection.NumberProducts
                nb_to_ingest += 1
                logger.info(f"{pds_collection} must be ingested")
        return (nb_to_ingest, nb_records)

    @UtilsMonitoring.timeit
    def check_update(self, source: CheckUpdateEnum, *args, **kwargs):
        match source:
            case CheckUpdateEnum.CHECK_CACHE:
                pds_collections: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collections_from_cache(
                    self.body, self.dataset_id
                )
                nb_to_ingest: int = self._check_collections_to_ingest(
                    pds_collections
                )
                logger.info(
                    f"""Summary:
            {nb_to_ingest} collection(s) to ingest from cache"""
                )

            case CheckUpdateEnum.CHECK_PDS:
                pds_collections_cache: List[
                    PdsRegistryModel
                ] = self.pds_registry.load_pds_collections_from_cache(
                    self.body, self.dataset_id
                )
                _, pds_collections = self.pds_registry.get_pds_collections(
                    self.body, self.dataset_id
                )
                nb_to_update: int = self._check_updates_from_PDS(
                    pds_collections, pds_collections_cache
                )
                (
                    nb_to_ingest,
                    nb_records,
                ) = self.check_collections_to_ingest_from_pds(
                    pds_collections, pds_collections_cache
                )
                logger.info(
                    f"""Summary:
            - {nb_to_ingest} collection(s) to ingest from PDS, i.e {nb_records} products
            - {nb_to_update} collection(s) to update"""
                )

            case _:
                raise NotImplementedError(
                    f"Check update is not implemented for {source}"
                )

    @UtilsMonitoring.timeit
    def transform(self, data: PdsDataEnum, *args, **kwargs):
        """Transform the downloaded information as STAC

        It exists different types of extraction:

        * PDS_RECORDS : Load the PDS collections from cache, convert to STAC items and parents if parents are not available
        * PDS_CATALOGS : Load the PDS collections from cache, convert/update to STAC the various catalogs/collections

        Args:
            data (PdsDataEnum): Type of transformation

        Raises:
            NotImplementedError: Transformation type is not implemented
        """
        pds_collections: List[
            PdsRegistryModel
        ] = self.pds_registry.load_pds_collections_from_cache(
            self.body, self.dataset_id
        )
        match data:
            case PdsDataEnum.PDS_CATALOGS:
                self.report.name = PdsDataEnum.PDS_CATALOGS.name
                self.report.start_report()
                self.stac_catalog_transformer.init()
                self.stac_catalog_transformer.to_stac(
                    self.pds_ode_catalogs,
                    pds_collections,
                    timeout=self.parser_timeout,
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
