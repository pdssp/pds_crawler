# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Module Name:
    pds3_objects

Description:
    Create a STAC output of the PDS collection by the use of PDS3 catalogs.
    The code defines an implementation of the Chain of Responsibility design
    pattern using the abstract base class Handler to select the handler (mission,
    plateform, instrument, dataset) to convert to STAC

Classes:
    Handler:
        Handler interface.
    AbstractHandler:
        Default chaining behavior.
    MissionHandler :
        Mission handler.
    PlateformHandler :
        Plateform handler.
    InstrumentHandler :
        Instrument handler.
    DatasetHandler :
        Dataset handler.
    StacPdsCollection :
        Converts PDS3 object from ODE archive to PDS STAC catalog (without items)

Author:
    Jean-Christophe Malapert
"""
from __future__ import annotations

import logging
from abc import ABC
from abc import abstractmethod
from typing import Any
from typing import cast
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import pystac

from ..load import PdsParserFactory
from ..models import DataSetModel
from ..models import InstrumentHostModel
from ..models import InstrumentModel
from ..models import MissionModel
from ..models import PdsRegistryModel
from ..models import ReferencesModel
from ..models import VolumeModel
from ..models.pds_models import DataProducerModel
from ..models.pds_models import DataSupplierModel

logger = logging.getLogger(__name__)


class Handler(ABC):
    """
    The Handler interface declares a method for building the chain of handlers.
    It also declares a method for executing a request.
    """

    @abstractmethod
    def set_next(self, handler: Handler) -> Handler:
        pass

    @abstractmethod
    def handle(self, request) -> None:
        pass


class AbstractHandler(Handler):
    """
    The default chaining behavior can be implemented inside a base handler
    class.
    """

    _next_handler: Optional[Handler] = None

    def set_next(self, handler: Handler) -> Handler:
        self._next_handler = handler
        return handler

    def _is_exists(
        self, mission_stac: Union[pystac.Catalog, pystac.Collection]
    ) -> bool:
        """Checks if the catalog or collection exists

        Args:
            catalog (pystac.Catalog): Stac Catalog or collection

        Returns:
            bool: True when the catalog or collection ID is in the STAC catalog
        """
        return mission_stac is not None

    @abstractmethod
    def handle(self, request: Any) -> None:
        if self._next_handler:
            self._next_handler.handle(request)


class MissionHandler(AbstractHandler):
    def __init__(
        self,
        catalog: pystac.Catalog,
        planet_id: str,
        mission_id,
        citations: Optional[ReferencesModel],
    ):
        self.__catalog: pystac.Catalog = catalog
        self.__planet_id: str = planet_id
        self.__mission_id: str = mission_id
        self.__citations: Optional[ReferencesModel] = citations

    @property
    def planet_id(self) -> str:
        return self.__planet_id

    @property
    def mission_id(self) -> str:
        return self.__mission_id

    @property
    def catalog(self) -> pystac.Catalog:
        return self.__catalog

    @property
    def citations(self) -> Optional[ReferencesModel]:
        return self.__citations

    def _is_must_be_updated(
        self, mission_stac: pystac.Catalog, mission: MissionModel
    ) -> bool:
        return (
            mission_stac.description
            != mission.MISSION_INFORMATION.MISSION_DESC
        )

    def _update(self, mission_stac: pystac.Catalog, mission: MissionModel):
        mission_stac_new = mission.create_stac_catalog(self.citations)
        mission_stac.title = mission_stac_new.title
        mission_stac.description = mission_stac.description
        mission_stac.stac_extensions = mission_stac.stac_extensions
        mission_stac.extra_fields = mission_stac.extra_fields
        mission_stac.save_object(include_self_link=False)

    def handle(self, request: Any) -> None:
        if isinstance(request, MissionModel):
            mission: MissionModel = request
            mission_stac = cast(
                pystac.Catalog,
                self.catalog.get_child(self.mission_id, recursive=True),
            )
            if not self._is_exists(mission_stac):
                stac_mission = mission.create_stac_catalog(self.citations)
                stac_mission.id = (
                    self.mission_id
                )  # use mission_id of PDS collection to avoid interop problem
                planet_cat = cast(
                    pystac.Catalog, self.catalog.get_child(self.planet_id)
                )
                planet_cat.add_child(stac_mission)
                logger.debug(f"{stac_mission.id} added to {planet_cat.id}")
            elif self._is_must_be_updated(mission_stac, mission):
                logger.info(f"{mission} has been updated")
                self._update(mission_stac, mission)
        else:
            super().handle(request)


class PlateformHandler(AbstractHandler):
    def __init__(
        self,
        catalog: pystac.Catalog,
        mission_id: str,
        citations: Optional[ReferencesModel],
    ):
        self.__catalog: pystac.Catalog = catalog
        self.__mission_id: str = mission_id
        self.__citations: Optional[ReferencesModel] = citations

    @property
    def catalog(self) -> pystac.Catalog:
        return self.__catalog

    @property
    def mission_id(self) -> str:
        return self.__mission_id

    @property
    def citations(self) -> Optional[ReferencesModel]:
        return self.__citations

    def _is_must_be_updated(
        self, plateform_stac: pystac.Catalog, plateform: InstrumentHostModel
    ) -> bool:
        return (
            plateform_stac.description
            != plateform.INSTRUMENT_HOST_INFORMATION.INSTRUMENT_HOST_DESC
        )

    def _update(
        self, plateform_stac: pystac.Catalog, plateform: InstrumentHostModel
    ):
        plateform_stac_new = plateform.create_stac_catalog(self.citations)
        plateform_stac.title = plateform_stac_new.title
        plateform_stac.description = plateform_stac_new.description
        plateform_stac.stac_extensions = plateform_stac_new.stac_extensions
        plateform_stac.extra_fields = plateform_stac_new.extra_fields
        plateform_stac.save_object(include_self_link=False)

    def _add_plateform_to_mission(self, plateform: InstrumentHostModel):
        plateform_id: str = plateform.get_plateform_id()
        plateform_stac = cast(
            pystac.Catalog,
            self.catalog.get_child(plateform_id, recursive=True),
        )
        if not self._is_exists(plateform_stac):
            stac_mission = cast(
                pystac.Catalog,
                self.catalog.get_child(self.mission_id, recursive=True),
            )
            logger.debug(f"Looking for {self.mission_id}: {stac_mission}")
            stac_plateform = plateform.create_stac_catalog(self.citations)
            stac_mission.add_child(stac_plateform)
            logger.debug(f"{stac_plateform.id} added to {stac_mission.id}")
        elif self._is_must_be_updated(plateform_stac, plateform):
            logger.info(f"{plateform} has been updated")
            self._update(plateform_stac, plateform)

    def _add_plateforms_to_mission(
        self, plateforms: List[InstrumentHostModel]
    ):
        for plateform in plateforms:
            self._add_plateform_to_mission(plateform)

    def handle(self, request: Any) -> None:
        if isinstance(request, InstrumentHostModel):
            plateform: InstrumentHostModel = request
            self._add_plateform_to_mission(plateform)
        elif isinstance(request, list) and isinstance(
            request[0], InstrumentHostModel
        ):
            plateforms: List[InstrumentHostModel] = request
            self._add_plateforms_to_mission(plateforms)
        else:
            super().handle(request)


class InstrumentHandler(AbstractHandler):
    def __init__(
        self, catalog: pystac.Catalog, citations: Optional[ReferencesModel]
    ):
        self.__catalog: pystac.Catalog = catalog
        self.__citations: Optional[ReferencesModel] = citations

    @property
    def catalog(self) -> pystac.Catalog:
        return self.__catalog

    @property
    def citations(self) -> Optional[ReferencesModel]:
        return self.__citations

    def _is_must_be_updated(
        self, instrument_stac: pystac.Catalog, instrument: InstrumentModel
    ) -> bool:
        return (
            instrument_stac.description
            != instrument.INSTRUMENT_INFORMATION.INSTRUMENT_DESC
        )

    def _update(
        self, instrument_stac: pystac.Catalog, instrument: InstrumentModel
    ):
        instrument_stac_new = instrument.create_stac_catalog(self.citations)
        instrument_stac.title = instrument_stac_new.title
        instrument_stac.description = instrument_stac_new.description
        instrument_stac.stac_extensions = instrument_stac_new.stac_extensions
        instrument_stac.extra_fields = instrument_stac_new.extra_fields
        instrument_stac.save_object(include_self_link=False)

    def _add_instrument_to_mission(self, instrument: InstrumentModel):
        instrument_id: str = instrument.get_instrument_id()
        instrument_stac = cast(
            pystac.Catalog,
            self.catalog.get_child(instrument_id, recursive=True),
        )
        if not self._is_exists(instrument_stac):
            plateform_id: str = instrument.get_plateform_id()
            stac_plateform = cast(
                pystac.Catalog,
                self.catalog.get_child(plateform_id, recursive=True),
            )
            logger.debug(f"Looking for {plateform_id}: {stac_plateform}")
            stac_instrument = instrument.create_stac_catalog(self.citations)
            stac_plateform.add_child(stac_instrument)
            logger.debug(f"{stac_instrument.id} added to {stac_plateform.id}")
        elif self._is_must_be_updated(instrument_stac, instrument):
            logger.info(f"{instrument} has been updated")
            self._update(instrument_stac, instrument)

    def _add_instruments_to_mission(self, instruments: List[InstrumentModel]):
        for instrument in instruments:
            self._add_instrument_to_mission(instrument)

    def handle(self, request: Any) -> None:
        if isinstance(request, InstrumentModel):
            instrument: InstrumentModel = request
            self._add_instrument_to_mission(instrument)
        elif isinstance(request, list) and isinstance(
            request[0], InstrumentModel
        ):
            instruments: List[InstrumentModel] = request
            self._add_instruments_to_mission(instruments)
        else:
            super().handle(request)


class DatasetHandler(AbstractHandler):
    def __init__(
        self,
        catalog: pystac.Catalog,
        volume_desc: VolumeModel,
        citations: Optional[ReferencesModel],
    ):
        self.__catalog: pystac.Catalog = catalog
        self.__citations: Optional[ReferencesModel] = citations
        self.__data_supplier: Optional[
            DataSupplierModel
        ] = volume_desc.DATA_SUPPLIER
        self.__data_producer: DataProducerModel = volume_desc.DATA_PRODUCER

    @property
    def catalog(self) -> pystac.Catalog:
        return self.__catalog

    @property
    def data_supplier(self) -> Optional[DataSupplierModel]:
        return self.__data_supplier

    @property
    def data_producer(self) -> DataProducerModel:
        return self.__data_producer

    @property
    def citations(self) -> Optional[ReferencesModel]:
        return self.__citations

    def _is_must_be_updated(
        self, dataset_stac: pystac.Collection, dataset: DataSetModel
    ) -> bool:
        return (
            dataset_stac.description
            != dataset.DATA_SET_INFORMATION._get_description()
        )

    def _update(self, dataset_stac: pystac.Collection, dataset: DataSetModel):
        dataset_stac_new = dataset.create_stac_collection(
            self.citations, self.data_supplier, self.data_producer
        )
        dataset_stac.title = dataset_stac_new.title
        dataset_stac.description = dataset_stac_new.description
        dataset_stac.stac_extensions = dataset_stac_new.stac_extensions
        dataset_stac.extra_fields = dataset_stac_new.extra_fields
        dataset_stac.save_object(include_self_link=False)

    def _add_dataset_to_instrument(self, dataset: DataSetModel):
        dataset_id: str = dataset.get_collection_id()
        dataset_stac = cast(
            pystac.Collection,
            self.catalog.get_child(dataset_id, recursive=True),
        )
        if not self._is_exists(dataset_stac):
            instrument_id: str = dataset.DATA_SET_HOST.get_instrument_id()
            stac_instrument = cast(
                pystac.Catalog,
                self.catalog.get_child(instrument_id, recursive=True),
            )
            logger.debug(f"Looking for {instrument_id}: {stac_instrument}")
            stac_dataset = dataset.create_stac_collection(
                self.citations, self.data_supplier, self.data_producer
            )
            stac_instrument.add_child(stac_dataset)
            logger.debug(f"{stac_dataset.id} added to {stac_instrument.id}")
        elif self._is_must_be_updated(dataset_stac, dataset):
            logger.info(f"{dataset} has been updated")
            self._update(dataset_stac, dataset)

    def _add_datasets_to_instrument(self, datasets: List[DataSetModel]):
        for dataset in datasets:
            self._add_dataset_to_instrument(dataset)

    def handle(self, request: Any) -> None:
        if isinstance(request, DataSetModel):
            dataset: DataSetModel = request
            self._add_dataset_to_instrument(dataset)
        elif isinstance(request, list) and isinstance(
            request[0], DataSetModel
        ):
            datasets: List[DataSetModel] = request
            self._add_datasets_to_instrument(datasets)
        else:
            super().handle(request)


class StacPdsCollection:
    SORT_ORDER = {
        PdsParserFactory.FileGrammary.MISSION_CATALOG.name: 0,
        PdsParserFactory.FileGrammary.INSTRUMENT_HOST_CATALOG.name: 1,
        PdsParserFactory.FileGrammary.INSTRUMENT_CATALOG.name: 2,
        PdsParserFactory.FileGrammary.DATA_SET_CATALOG.name: 3,
        PdsParserFactory.FileGrammary.DATA_SET_MAP_PROJECTION_CATALOG.name: 4,
        PdsParserFactory.FileGrammary.PERSONNEL_CATALOG.name: 5,
        PdsParserFactory.FileGrammary.REFERENCE_CATALOG.name: 6,
        PdsParserFactory.FileGrammary.VOL_DESC.name: 7,
        "collection": 8,
    }

    def __init__(self, root_stac: pystac.Catalog):
        self.__root_stac: pystac.Catalog = root_stac
        self.__catalogs: Dict[str, Any] = dict()

    def _is_already_exists(self, id: str) -> bool:
        """Checks if the catalog or collection ID is in the STAC catalog

        Args:
            id (str): catalog or collection ID

        Returns:
            bool: True when the catalog or collection ID is in the STAC catalog
        """
        return self.root_stac.get_child(id, recursive=True) is not None

    @property
    def catalogs(self) -> Dict[str, Any]:
        return self.__catalogs

    @catalogs.setter
    def catalogs(self, value: Dict[str, Any] = dict()):
        self.__catalogs = value

    @property
    def root_stac(self) -> pystac.Catalog:
        return self.__root_stac

    def to_stac(self):
        # Get the PDS3 reference catalog
        ref_catalog_name: str = (
            PdsParserFactory.FileGrammary.REFERENCE_CATALOG.name
        )
        citations: ReferencesModel = cast(
            ReferencesModel, self.catalogs.get(ref_catalog_name)
        )

        # Get the PDS3 collection
        pds_collection: PdsRegistryModel = cast(
            PdsRegistryModel, self.catalogs.get("collection")
        )

        # Get the volume description catalog that contains a reference
        # to others catalogs
        vol_catalog_name: str = PdsParserFactory.FileGrammary.VOL_DESC.name
        volume_desc: VolumeModel = cast(
            VolumeModel, self.catalogs.get(vol_catalog_name)
        )
        planet_id: str = pds_collection.get_planet_id()
        mission_id: str = pds_collection.get_mission_id()
        if not self._is_already_exists(planet_id):
            pystac_planet_cat = pds_collection.create_stac_planet_catalog()
            self.root_stac.add_child(pystac_planet_cat)

        mission = MissionHandler(
            self.root_stac, planet_id, mission_id, citations
        )
        plateform = PlateformHandler(self.root_stac, mission_id, citations)
        instrument = InstrumentHandler(self.root_stac, citations)
        dataset = DatasetHandler(self.root_stac, volume_desc, citations)
        mission.set_next(plateform).set_next(instrument).set_next(dataset)

        catalogs = list(self.catalogs.keys())
        catalogs.sort(key=lambda val: StacPdsCollection.SORT_ORDER[val])
        for catalog_name in catalogs:
            logger.debug(f"\nProcessing {catalog_name}")
            catalog = self.catalogs[catalog_name]
            mission.handle(catalog)
