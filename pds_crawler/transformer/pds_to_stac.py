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
from multiprocessing import Pool
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
from ..models import PdsRecordModel
from ..models import PdsRecordsModel
from ..models import PdsRegistryModel
from ..report import MessageModel
from ..utils import Observable
from ..utils import ProgressLogger
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
        self,
        pds_records: PdsRecordsWs,
        pds_collection: PdsRegistryModel,
        progress_bar: bool = True,
    ) -> pystac.ItemCollection:
        """Creates a collection of STAC items of records from a PDS collection.

        The records are loaded from the local storage, handled by `PdsRecord`

        Args:
            pds_records (PdsRecordsWs): Object that handle Records
            pds_collection (PdsRegistryModel): PDS collection data
            progress_bar (bool, optional) : Set progress bar. Defaults to True

        Returns:
            pystac.ItemCollection: Collection of items
        """

        def create_items(
            pages: Iterator[PdsRecordsModel],
            pds_collection: PdsRegistryModel,
            progress_bar: bool = True,
        ) -> Iterable[pystac.Item]:
            """Creates items

            Args:
                pages (Iterator[PdsRecordsModel]): the different pages of the web service response
                pds_collection (PdsRegistryModel): information about the collection
                progress_bar (bool, optional) : Set progress bar. Defaults to True

            Returns:
                Iterable[pystac.Item]: Items

            Yields:
                Iterator[Iterable[pystac.Item]]: Items
            """
            for page in pages:
                pds_records_model = page.pds_records_model
                with ProgressLogger(
                    total=len(pds_records_model),
                    iterable=pds_records_model,
                    logger=logger,
                    description="STAC Item objects creation",
                    position=2,
                    leave=False,
                    disable_tqdm=not progress_bar,
                ) as pds_records_model_pbar:
                    for record in cast(
                        List[PdsRecordModel], pds_records_model_pbar
                    ):
                        if self.database.stac_storage.item_exists(record):
                            continue
                        try:
                            yield record.to_stac_item(pds_collection)
                        except CrawlerError as err:
                            self.notify_observers(
                                MessageModel(record.ode_id, err)
                            )

        pages: Iterator[
            PdsRecordsModel
        ] = pds_records.parse_pds_collection_from_cache(pds_collection)
        return pystac.ItemCollection(
            create_items(pages, pds_collection, progress_bar=progress_bar)
        )

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

    def _pds_collection_to_stac(
        self,
        pds_collection: List[PdsRegistryModel],
        items_stac: pystac.ItemCollection,
    ):
        """Creates the PDS collection to STAC

        Args:
            pds_collection (List[PdsRegistryModel]): PDS collection
            items_stac (pystac.ItemCollection): items
        """
        catalogs_ids = [
            pds_collection.get_body_id(),
            pds_collection.get_mission_id(),
            pds_collection.get_plateform_id(),
            pds_collection.get_instrument_id(),
            pds_collection.get_collection_id(),
        ]

        new_catalog: Optional[Union[pystac.Catalog, pystac.Collection]] = None

        for catalog_id in catalogs_ids:
            stac_catalog = cast(
                pystac.Catalog,
                self.catalog.get_child(catalog_id, recursive=True),
            )
            if not self._is_exist(stac_catalog):
                if catalog_id == pds_collection.get_body_id():
                    stac_catalog = pds_collection.create_stac_body_catalog()
                    self.catalog.add_child(stac_catalog)
                elif catalog_id == pds_collection.get_mission_id():
                    stac_catalog = pds_collection.create_stac_mission_catalog()
                    self.catalog.get_child(
                        pds_collection.get_body_id(), recursive=True
                    ).add_child(stac_catalog)
                elif catalog_id == pds_collection.get_plateform_id():
                    stac_catalog = (
                        pds_collection.create_stac_platform_catalog()
                    )
                    self.catalog.get_child(
                        pds_collection.get_mission_id(), recursive=True
                    ).add_child(stac_catalog)
                elif catalog_id == pds_collection.get_instrument_id():
                    stac_catalog = pds_collection.create_stac_instru_catalog()
                    self.catalog.get_child(
                        pds_collection.get_plateform_id(), recursive=True
                    ).add_child(stac_catalog)
                elif catalog_id == pds_collection.get_collection_id():
                    stac_catalog = pds_collection.create_stac_collection()
                    self.catalog.get_child(
                        pds_collection.get_instrument_id(), recursive=True
                    ).add_child(stac_catalog)
                else:
                    raise ValueError(f"Undefined catalog : {catalog_id}")
                if new_catalog is None:
                    new_catalog = stac_catalog
            else:
                logger.debug(
                    f"Catalog {stac_catalog.id} already exists, skip it"
                )

        if new_catalog is not None:
            self.database.stac_storage.normalize_and_save(new_catalog)

        stac_collection = self.catalog.get_child(
            pds_collection.get_collection_id(), recursive=True
        )
        if stac_collection.get_item_links() != len(items_stac):
            stac_collection.add_items(items_stac)
            self.database.stac_storage.normalize_and_save(stac_collection)

        if new_catalog is not None:
            parent = new_catalog.get_parent()
            parent.save_object(include_self_link=False)

    def to_stac(
        self,
        pds_records: PdsRecordsWs,
        pds_collections: List[PdsRegistryModel],
        progress_bar: bool = True,
    ):
        """Create STAC catalogs with its children for all collections.

        Args:
            pds_records (PdsRecordsWs): Web service that handles the query to get the responses for a given collection
            pds_collections (List[PdsRegistryModel]): All PDS collections data
            progress_bar (bool, optional): Set progress bar. Defaults to True
        """
        # Create a progress logger to track the processing of collections
        with ProgressLogger(
            total=len(pds_collections),
            iterable=pds_collections,
            logger=logger,
            description="Processing collection",
            position=0,
            disable_tqdm=not progress_bar,
        ) as progress_logger:
            # Iterate over each PDS collection and process it
            for pds_collection in cast(
                List[PdsRegistryModel], progress_logger
            ):
                progress_logger.write_msg(
                    f"Processing the collection {pds_collection}"
                )

                # Create items for the current collection
                items_stac = self._create_items_stac(
                    pds_records, pds_collection, progress_bar=progress_bar
                )
                if len(items_stac.items) == 0:
                    progress_logger.write_msg(
                        "No new item, skip the STAC catalogs creation"
                    )
                    continue
                else:
                    progress_logger.write_msg(
                        f"{len(items_stac.items)} items to add"
                    )
                self._pds_collection_to_stac(pds_collection, items_stac)
                del items_stac

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
            logger.info(f"Creating STAC catalog for {catalogs_pds_collection}")
            self.__stac_pds_collection.catalogs = catalogs_pds_collection
            self.__stac_pds_collection.to_stac()

    def to_stac(
        self,
        pds_ode_catalogs: PDSCatalogsDescription,
        pds_collections: List[PdsRegistryModel],
        **kwargs,
    ):
        """Creates the STAC catalog and its children.

        Args:
            pds_ode_catalogs (PDSCatalogsDescription): PDS3 objects
            pds_collections (List[PdsRegistryModel]): PDS Collection data
        """
        catalogs: Iterator[Dict[str, Any]] = pds_ode_catalogs.get_ode_catalogs(
            pds_collections, kwargs.get("timeout", 30)
        )
        self._build_stac_cats_and_colls_for_all_pds_catalogs(catalogs)

    def describe(self):
        """Describe the catalog"""
        self.catalog.describe()

    def save(self):
        """Save on disk the catalog"""
        self.database.stac_storage.root_normalize_and_save(self.catalog)
