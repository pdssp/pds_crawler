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
import os
from abc import ABC
from typing import Any
from typing import Dict
from typing import Iterable
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union

import pystac
from tqdm import tqdm

from ..exception import CrawlerError
from ..load import Database
from ..report import MessageModel
from ..utils import Observable
from pds_crawler.extractor import PDSCatalogsDescription
from pds_crawler.extractor import PdsRecords
from pds_crawler.load import PdsParserFactory
from pds_crawler.models import DataSetModel
from pds_crawler.models import InstrumentHostModel
from pds_crawler.models import InstrumentModel
from pds_crawler.models import MissionModel
from pds_crawler.models import PdsRecordModel
from pds_crawler.models import PdsRecordsModel
from pds_crawler.models import PdsRegistryModel
from pds_crawler.models import ReferencesModel
from pds_crawler.models import VolumeModel
from pds_crawler.models.pds_models import DataProducerModel
from pds_crawler.models.pds_models import DataSupplierModel

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
        return self.__database


class StacRecordsTransformer(StacTransformer):
    """Convert the records to STAC."""

    def __init__(
        self,
        database: Database,
        *args,
        **kwargs,
    ):
        super().__init__(database)
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.init()

    def init(self):
        self.__catalog: pystac.Catalog = None

    @property
    def catalog(self) -> pystac.Catalog:
        return self.__catalog

    def load_root_catalog(self):
        """Loads the root catalog"""
        self.__catalog = pystac.Catalog.from_file(
            os.path.join(self.database.stac_directory, "catalog.json")
        )

    def _create_items_stac(
        self, pds_records: PdsRecords, pds_collection: PdsRegistryModel
    ) -> pystac.ItemCollection:
        """Creates a collection of STAC items of records from a PDS collection.

        The records are loaded from the local storage, handled by `PdsRecord`

        Args:
            pds_records (PdsRecords): Object that handle Records
            pds_collection (PdsRegistryModel): PDS collection data

        Returns:
            pystac.ItemCollection: Collection of items
        """

        def create_items(
            pages: Iterator[PdsRecordsModel], pds_collection: PdsRegistryModel
        ) -> Iterable[pystac.Item]:
            for page in pages:
                for record in tqdm(
                    page.pds_records_model,
                    desc="STAC Item objects creation",
                    total=len(page.pds_records_model),
                    position=2,
                    leave=False,
                ):
                    directory: str = os.path.join(
                        self.database.stac_directory,
                        record.get_planet_id(),
                        record.get_mission_id(),
                        record.get_plateform_id(),
                        record.get_instrument_id(),
                        record.get_collection_id(),
                        record.get_id(),
                    )
                    if os.path.exists(directory):
                        logger.warning(
                            f"this record exists in {directory}, skip it"
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
        pds_records: PdsRecords,
        pds_collections: List[PdsRegistryModel],
    ):
        """Create a STAC catalogs with its children.

        Args:
            pds_records (PdsRecords): Objcet that handle the PDS records
            pds_collections (List[PdsRegistryModel]): All PDS collections data
        """
        for pds_collection in tqdm(
            pds_collections,
            desc="Processing collection",
            total=len(pds_collections),
            position=0,
        ):
            tqdm.write(f"Processing the collection {pds_collection}")
            items_stac = self._create_items_stac(pds_records, pds_collection)
            if len(items_stac.items) == 0:
                tqdm.write("No new item, skip the STAC catalogs creation")
                continue
            else:
                tqdm.write(f"{len(items_stac.items)} items to add")

            stac_collection: pystac.Collection = self.catalog.get_child(
                pds_collection.get_collection_id(), recursive=True
            )
            stac_instru: pystac.Catalog = self.catalog.get_child(
                pds_collection.get_instrument_id(), recursive=True
            )
            stac_host: pystac.Catalog = self.catalog.get_child(
                pds_collection.get_plateform_id(), recursive=True
            )
            stac_mission: pystac.Catalog = self.catalog.get_child(
                pds_collection.get_mission_id(), recursive=True
            )
            stac_planet: pystac.Catalog = self.catalog.get_child(
                pds_collection.get_planet_id()
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
                stac_collection.save()
                parent = stac_collection.get_parent()
                parent.save_object(include_self_link=False)
            else:
                new_catalog.save()
                parent = new_catalog.get_parent()
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
        self.__catalog = pystac.Catalog(
            id="urn:pdssp:pds",
            title="Planetary Data System",
            description="Georeferenced data extracted from ode.rsl.wustl.edu",
        )
        self.__catalog.add_link(
            pystac.Link(
                rel=pystac.RelType.PREVIEW,
                target="https://pdsmgmt.gsfc.nasa.gov/images/PDS_Logo.png",
                title="PDS logo",
                media_type=pystac.MediaType.PNG,
            )
        )

    @property
    def catalog(self) -> pystac.Catalog:
        """Returns the root catalog

        Returns:
            pystac.Catalog: the root catalog
        """
        return self.__catalog

    def _has_mission(self, catalog: Any) -> bool:
        """Checks if the catalog contains the PDS3 object of the mission

        Args:
            catalog (Any): list of PDS3 objets

        Returns:
            bool: True when the catalog contains the PDS3 object of the mission otherwise False
        """
        return PdsParserFactory.FileGrammary.MISSION_CATALOG.name in catalog

    def _has_plateform(self, catalog: Any) -> bool:
        """Checks if the catalog contains the PDS3 object of the plateform

        Args:
            catalog (Any): list of PDS3 objets

        Returns:
            bool: True when the catalog contains the PDS3 object of the plateform otherwise False
        """
        return (
            PdsParserFactory.FileGrammary.INSTRUMENT_HOST_CATALOG.name
            in catalog
        )

    def _has_instrument(self, catalog: Any) -> bool:
        """Checks if the catalog contains the PDS3 object of the instrument

        Args:
            catalog (Any): list of PDS3 objets

        Returns:
            bool: True when the catalog contains the PDS3 object of the instrument otherwise False
        """
        return PdsParserFactory.FileGrammary.INSTRUMENT_CATALOG.name in catalog

    def _has_collection(self, catalog: Any) -> bool:
        """Checks if the catalog contains the PDS3 object of the dataset

        Args:
            catalog (Any): list of PDS3 objets

        Returns:
            bool: True when the catalog contains the PDS3 object of the dataset otherwise False
        """
        return PdsParserFactory.FileGrammary.DATA_SET_CATALOG.name in catalog

    def _is_already_exists(self, id: str) -> bool:
        """Checks if the catalog or collection ID is in the STAC catalog

        Args:
            id (str): catalog or collection ID

        Returns:
            bool: True when the catalog or collection ID is in the STAC catalog
        """
        return self.catalog.get_child(id, recursive=True) is not None

    def _add_plateforms_to_mission(
        self,
        plateforms: List[InstrumentHostModel],
        mission_id: str,
        references: Optional[ReferencesModel] = None,
    ):
        """Creates a Plateform STAC catalogs and add them to the mission STAC catalog if
        one of the plateform does not exist

        References are used to add citations in the plateform STAC catalog.

        Args:
            plateforms (List[InstrumentHostModel]): plateforms
            mission_id (str): mission ID
            references (Optional[ReferencesModel], optional): _description_. Defaults to None.
        """
        for plateform in plateforms:
            self._add_plateform_to_mission(plateform, mission_id, references)

    def _add_plateform_to_mission(
        self,
        plateform: InstrumentHostModel,
        mission_id: str,
        references: Optional[ReferencesModel] = None,
    ):
        """Creates a Plateform STAC catalog and add it to the mission STAC catalog if
        the plateform does not exist

        References are used to add citations in the plateform STAC catalog.

        Args:
            plateform (InstrumentHostModel): plateform
            mission_id (str): mission ID
            references (Optional[ReferencesModel], optional): citations. Defaults to None.
        """
        pystac_plateform_cat: pystac.Catalog = plateform.create_stac_catalog(
            references
        )
        if not self._is_already_exists(pystac_plateform_cat.id):
            self.catalog.get_child(mission_id, recursive=True).add_child(
                pystac_plateform_cat
            )

    def _add_instruments_to_plateform(
        self,
        instruments: List[InstrumentModel],
        references: Optional[ReferencesModel] = None,
    ):
        """Creates an Instrument STAC catalogs and add them to the plateform STAC catalog if
        one of the instrument does not exist

        References are used to add citations in the plateform STAC catalog.

        Args:
            instruments (List[InstrumentHostModel]): instrument
            references (Optional[ReferencesModel], optional): _description_. Defaults to None.
        """
        for instru in instruments:
            self._add_instrument_to_plateform(instru, references)

    def _add_instrument_to_plateform(
        self,
        instrument: InstrumentModel,
        references: Optional[ReferencesModel] = None,
    ):
        """Creates a Instrument STAC catalog and add it to the plateform STAC catalog if
        the instrument does not exist

        References are used to add citations in the plateform STAC catalog.

        Args:
            instrument (InstrumentHostModel): instrument
            references (Optional[ReferencesModel], optional): citations. Defaults to None.
        """
        pystac_instru_cat: pystac.Catalog = instrument.create_stac_catalog(
            references
        )
        if not self._is_already_exists(instrument.get_instrument_id()):
            self.catalog.get_child(
                instrument.get_plateform_id(), recursive=True
            ).add_child(pystac_instru_cat)

    def _add_collections_to_instrument(
        self,
        collections: List[DataSetModel],
        references: Optional[ReferencesModel] = None,
        data_supplier: Optional[DataSupplierModel] = None,
        data_producer: Optional[DataProducerModel] = None,
    ):
        """Creates Datasets STAC collections and add them to the instrument STAC catalog if
        the dataset does not exist.

        References are used to add citations in the collection STAC catalog.

        Args:
            collections (List[DataSetModel]): datasets
            references (Optional[ReferencesModel], optional): citations. Defaults to None.
            data_supplier (Optional[DataSupplierModel], optional): data supplier. Defaults to None,
            data_producer: (Optional[DataProducerModel], optional): data producer. Defaults to None
        """
        for collection in collections:
            self._add_collection_to_instrument(
                collection, references, data_supplier, data_producer
            )

    def _add_collection_to_instrument(
        self,
        collection: DataSetModel,
        references: Optional[ReferencesModel] = None,
        data_supplier: Optional[DataSupplierModel] = None,
        data_producer: Optional[DataProducerModel] = None,
    ):
        """Creates a Dataset STAC collections and add it to the instrument STAC catalog if
        the dataset does not exist.

        References are used to add citations in the collection STAC catalog.

        Args:
            collections (DataSetModel): dataset
            references (Optional[ReferencesModel], optional): citations. Defaults to None.
            data_supplier (Optional[DataSupplierModel], optional): data supplier. Defaults to None,
            data_producer: (Optional[DataProducerModel], optional): data producer. Defaults to None
        """
        collection_id: str = collection.DATA_SET_ID
        if not self._is_already_exists(collection_id):
            instrument_id: str = collection.DATA_SET_HOST.get_instrument_id()
            stac_collection: pystac.Catalog = (
                collection.create_stac_collection(
                    references, data_supplier, data_producer
                )
            )
            self.catalog.get_child(instrument_id, recursive=True).add_child(
                stac_collection
            )

    def _build_stac_catalogs_and_collections(
        self, catalogs: Iterator[Dict[str, Any]]
    ):
        """Builds STAC catalogs and collections

        Args:
            catalogs (Iterator[Dict[str, Any]]): Catalogs to convert to STAC
        """
        for catalog in catalogs:
            stac_mission: pystac.Catalog
            references_ode: ReferencesModel = catalog.get(
                PdsParserFactory.FileGrammary.REFERENCE_CATALOG.name
            )
            pds_collection: PdsRegistryModel = catalog.get("collection")
            volume_desc: VolumeModel = catalog.get("volume")

            if not self._is_already_exists(pds_collection.get_planet_id()):
                pystac_planet_cat = pds_collection.create_stac_planet_catalog()
                self.catalog.add_child(pystac_planet_cat)

            if self._has_mission(catalog):
                mission_ode_cat: MissionModel = catalog[
                    PdsParserFactory.FileGrammary.MISSION_CATALOG.name
                ]
                stac_mission = mission_ode_cat.create_stac_catalog(
                    references_ode
                )
                if not self._is_already_exists(stac_mission.id):
                    self.catalog.get_child(
                        pds_collection.get_planet_id()
                    ).add_child(stac_mission)
            else:
                self.notify_observers(
                    MessageModel(
                        pds_collection.get_mission(),
                        f"Unable to get mission in {pds_collection}",
                    )
                )

            if self._has_mission(catalog) and self._has_plateform(catalog):
                plateform_ode_cat = catalog[
                    PdsParserFactory.FileGrammary.INSTRUMENT_HOST_CATALOG.name
                ]
                if isinstance(plateform_ode_cat, list):
                    self._add_plateforms_to_mission(
                        plateform_ode_cat,
                        stac_mission.id,
                        references_ode,
                    )
                else:
                    self._add_plateform_to_mission(
                        plateform_ode_cat,
                        stac_mission.id,
                        references_ode,
                    )
            else:
                self.notify_observers(
                    MessageModel(
                        pds_collection.get_plateform(),
                        f"Unable to get plateform in {pds_collection}",
                    )
                )

            if (
                self._has_mission(catalog)
                and self._has_plateform(catalog)
                and self._has_instrument(catalog)
            ):
                instru_ode_cat = catalog[
                    PdsParserFactory.FileGrammary.INSTRUMENT_CATALOG.name
                ]
                if isinstance(instru_ode_cat, list):
                    self._add_instruments_to_plateform(
                        instru_ode_cat, references_ode
                    )
                else:
                    self._add_instrument_to_plateform(
                        instru_ode_cat, references_ode
                    )
            else:
                self.notify_observers(
                    MessageModel(
                        pds_collection.get_instrument(),
                        f"Unable to get instrument in {pds_collection}",
                    )
                )

            if (
                self._has_mission(catalog)
                and self._has_plateform(catalog)
                and self._has_instrument(catalog)
                and self._has_collection(catalog)
            ):
                collection_ode_cat = catalog[
                    PdsParserFactory.FileGrammary.DATA_SET_CATALOG.name
                ]
                data_supplier = volume_desc.DATA_SUPPLIER
                data_producer = volume_desc.DATA_PRODUCER
                if isinstance(collection_ode_cat, list):
                    self._add_collections_to_instrument(
                        collection_ode_cat,
                        references_ode,
                        data_supplier,
                        data_producer,
                    )
                else:
                    self._add_collection_to_instrument(
                        collection_ode_cat,
                        references_ode,
                        data_supplier,
                        data_producer,
                    )
            else:
                self.notify_observers(
                    MessageModel(
                        pds_collection.get_collection(),
                        f"Unable to get dataset in {pds_collection}",
                    )
                )

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
        self._build_stac_catalogs_and_collections(catalogs)

    def describe(self):
        """Describe the catalog"""
        self.catalog.describe()

    def save(self):
        """Save on disk the catalog"""
        self.catalog.normalize_and_save(
            self.database.stac_directory,
            catalog_type=pystac.CatalogType.SELF_CONTAINED,
        )
