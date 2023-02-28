# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Module Name:
    pds_to_stac

Description:
    the pds_to_stac module convert the PDS3 objects and records from ODE web service to a unique
    STAC PDS catalog.

Classes:
    StacTransformer:
        Abstract class.
    StacRecordsTransformer :
        Converts records from ODE webservice to PDS STAC catalog.
    StacCatalogTransformer :
        Converts PDS3 object from ODE archive to PDS STAC catalog (without items)

Author:
    Jean-Christophe Malapert
"""
import logging
from abc import ABC
from typing import Any
from typing import cast
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union

import pystac
from tqdm import tqdm

from ..exception import CrawlerError
from ..extractor import PDSCatalogsDescription
from ..extractor import PdsRecordsWs
from ..load import Database
from ..models import PdsRecordsModel
from ..models import PdsRegistryModel
from ..report import MessageModel
from ..utils import Observable
from .pds3_objects import StacPdsCollection

logger = logging.getLogger(__name__)


class StacTransformer(ABC, Observable):
    """Abstract class for STAC transformation"""

    def __init__(self, database: Database):
        super().__init__()
        if not isinstance(database, Database):
            raise TypeError(
                "[StacTransformer] must be initialized with database attribute of type Dtabase."
            )
        self.__database = database

    @property
    def database(self) -> Database:
        """Returns the database

        Returns:
            Database: Database
        """
        return self.__database


class StacRecordsTransformer(StacTransformer):
    """Convert the records to STAC."""

    def __init__(
        self,
        database: Database,
        *args,
        **kwargs,
    ):
        """Init the transformer of :class:`pds_crawler.extractor.PdsRecordModel`
        provided by the response :class:`pds_crawler.extractor.PdsRecordsWs`

        In addition, it is possible to pass a class by *report* keyword
        to notify information to this class

        Args:
            database (Database): Database
        """
        super().__init__(database)
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.init()

    def init(self):
        self.__catalog: pystac.Catalog

    @property
    def catalog(self) -> pystac.Catalog:
        """Return a pySTAC catalog

        Returns:
            pystac.Catalog: pySTAC catalog
        """
        return self.__catalog

    def load_root_catalog(self):
        """Loads the root catalog"""
        self.database.stac_storage.refresh()
        self.__catalog = cast(
            pystac.Catalog, self.database.stac_storage.root_catalog
        )

    def _create_items_stac(
        self, pds_records: PdsRecordsWs, pds_collection: PdsRegistryModel
    ) -> pystac.ItemCollection:
        """Creates a collection of STAC items of records from a PDS collection.

        The records are loaded from the local storage, handled by `PdsRecord`

        Args:
            pds_records (PdsRecordsWs): Object that handle Records
            pds_collection (PdsRegistryModel): PDS collection data

        Returns:
            pystac.ItemCollection: Collection of items
        """

        def create_items(
            pages: Iterator[PdsRecordsModel], pds_collection: PdsRegistryModel
        ) -> Iterable[pystac.Item]:
            """Creates items

            Args:
                pages (Iterator[PdsRecordsModel]): the different pages of the web service response
                pds_collection (PdsRegistryModel): information about the collection

            Returns:
                Iterable[pystac.Item]: Items

            Yields:
                Iterator[Iterable[pystac.Item]]: Items
            """
            for page in pages:
                for record in tqdm(
                    page.pds_records_model,
                    desc="STAC Item objects creation",
                    total=len(page.pds_records_model),
                    position=2,
                    leave=False,
                ):
                    if self.database.stac_storage.item_exists(record):
                        logger.warning(
                            f"this {record} exists in STAC directory, skip it"
                        )
                        continue
                    try:
                        yield record.to_stac_item(pds_collection)
                    except CrawlerError as err:
                        self.notify_observers(MessageModel(record.ode_id, err))

        pages: Iterator[
            PdsRecordsModel
        ] = pds_records.parse_pds_collection_from_cache(pds_collection)
        return pystac.ItemCollection(create_items(pages, pds_collection))

    def _is_exist(
        self, catlog_or_collection: Union[pystac.Catalog, pystac.Collection]
    ) -> bool:
        """Check if catlog_or_collection exists.

        Args:
            catlog_or_collection (Union[pystac.Catalog, pystac.Collection]): STAC catalog or collection

        Returns:
            bool: True when the catalog or the collection exists otherwise False
        """
        return catlog_or_collection is not None

    def to_stac(
        self,
        pds_records: PdsRecordsWs,
        pds_collections: List[PdsRegistryModel],
    ):
        """Create STAC catalogs with its children for all collections.

        Args:
            pds_records (PdsRecordsWs): Web service that handles the query to get the responses for a given collection
            pds_collections (List[PdsRegistryModel]): All PDS collections data
        """
        for pds_collection in tqdm(
            pds_collections,
            desc="Processing collection",
            total=len(pds_collections),
            position=0,
        ):
            tqdm.write(f"Processing the collection {pds_collection}")

            # Create items
            items_stac = self._create_items_stac(pds_records, pds_collection)
            if len(items_stac.items) == 0:
                tqdm.write("No new item, skip the STAC catalogs creation")
                continue
            else:
                tqdm.write(f"{len(items_stac.items)} items to add")

            # load STAC collection if it exists
            stac_collection = cast(
                pystac.Collection,
                self.catalog.get_child(
                    pds_collection.get_collection_id(), recursive=True
                ),
            )

            # load STAC instrument if it exists
            stac_instru = cast(
                pystac.Catalog,
                self.catalog.get_child(
                    pds_collection.get_instrument_id(), recursive=True
                ),
            )

            # load STAC plateform if it exists
            stac_host = cast(
                pystac.Catalog,
                self.catalog.get_child(
                    pds_collection.get_plateform_id(), recursive=True
                ),
            )

            # load STAC mission if it exists
            stac_mission: pystac.Catalog = cast(
                pystac.Catalog,
                self.catalog.get_child(
                    pds_collection.get_mission_id(), recursive=True
                ),
            )

            # load STAC planet if it exists
            stac_planet: pystac.Catalog = cast(
                pystac.Catalog,
                self.catalog.get_child(pds_collection.get_planet_id()),
            )

            new_catalog: Optional[
                Union[pystac.Catalog, pystac.Collection]
            ] = None

            if not self._is_exist(stac_planet):
                stac_planet: pystac.Catalog = (
                    pds_collection.create_stac_planet_catalog()
                )
                if new_catalog is None:
                    new_catalog = stac_planet
                self.catalog.add_child(stac_planet)

            if not self._is_exist(stac_mission):
                stac_mission: pystac.Catalog = (
                    pds_collection.create_stac_mission_catalog()
                )
                if new_catalog is None:
                    new_catalog = stac_mission
                stac_planet.add_child(stac_mission)

            if not self._is_exist(stac_host):
                stac_host: pystac.Catalog = (
                    pds_collection.create_stac_platform_catalog()
                )
                if new_catalog is None:
                    new_catalog = stac_host
                stac_mission.add_child(stac_host)

            if not self._is_exist(stac_instru):
                stac_instru: pystac.Catalog = (
                    pds_collection.create_stac_instru_catalog()
                )
                if new_catalog is None:
                    new_catalog = stac_instru
                stac_host.add_child(stac_instru)

            if not self._is_exist(stac_collection):
                stac_collection: pystac.Catalog = (
                    pds_collection.create_stac_collection()
                )
                if new_catalog is None:
                    new_catalog = stac_collection
                stac_instru.add_child(stac_collection)

            stac_collection.add_items(items_stac)

            if new_catalog is None:
                self.database.stac_storage.normalize_and_save(stac_collection)
                parent = cast(pystac.Collection, stac_collection.get_parent())
                parent.save_object(include_self_link=False)
            else:
                self.database.stac_storage.normalize_and_save(new_catalog)
                parent = cast(pystac.Catalog, new_catalog.get_parent())
                parent.save_object(include_self_link=False)

    def describe(self):
        """Describes the STAC catalog and its children as a tree"""
        self.catalog.describe()

    def save(self):
        """Nothing happens.
        Averything is saved in to_stac method"""
        pass


class StacCatalogTransformer(StacTransformer):
    """Converts the catalogs to STAC."""

    def __init__(self, database: Database, *args, **kwargs):
        """Initialises the object with database to get access to the data."""
        super().__init__(database)
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.init()

    def init(self):
        """Initialise the catalog"""
        self.database.stac_storage._load_root_catalog()
        self.__catalog = cast(
            pystac.Catalog, self.database.stac_storage.root_catalog
        )
        self.__stac_pds_collection = StacPdsCollection(self.__catalog)

    @property
    def catalog(self) -> pystac.Catalog:
        """Returns the root catalog

        Returns:
            pystac.Catalog: the root catalog
        """
        return self.__catalog

    def _build_stac_cats_and_colls_for_all_pds_catalogs(
        self, catalogs_pds_collections: Iterator[Dict[str, Any]]
    ):
        """Builds STAC catalogs and collections for all PDS collections

        Args:
            catalogs_pds_collections (Iterator[Dict[str, Any]]): Catalogs for all PDS collections
        """
        for catalogs_pds_collection in catalogs_pds_collections:
            self.__stac_pds_collection.catalogs = catalogs_pds_collection
            self.__stac_pds_collection.to_stac()

    def to_stac(
        self,
        pds_ode_catalogs: PDSCatalogsDescription,
        pds_collections: List[PdsRegistryModel],
    ):
        """Creates the STAC catalog and its children.

        Args:
            pds_ode_catalogs (PDSCatalogsDescription): PDS3 objects
            pds_collections (List[PdsRegistryModel]): PDS Collection data
        """
        catalogs: Iterator[Dict[str, Any]] = pds_ode_catalogs.get_ode_catalogs(
            pds_collections
        )
        self._build_stac_cats_and_colls_for_all_pds_catalogs(catalogs)

    def describe(self):
        """Describe the catalog"""
        self.catalog.describe()

    def save(self):
        """Save on disk the catalog"""
        self.database.stac_storage.root_normalize_and_save(self.catalog)
