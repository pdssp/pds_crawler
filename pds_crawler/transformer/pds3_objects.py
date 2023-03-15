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
import os
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
    """A handler for adding mission to a STAC catalog."""

    def __init__(
        self,
        catalog: pystac.Catalog,
        body_id: str,
        mission_id,
        citations: Optional[ReferencesModel],
    ):
        self.__catalog: pystac.Catalog = catalog
        self.__body_id: str = body_id
        self.__mission_id: str = mission_id
        self.__citations: Optional[ReferencesModel] = citations

    @property
    def body_id(self) -> str:
        return self.__body_id

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
        """Check if mission_stac must be updated.

        To check if mission_stac must be updated, we need to check :
        - mission_stac is alreay on disk
        - the description is shorter than the mission description

        Args:
            mission_stac (pystac.Catalog): mission in memory or in disk
            mission (MissionModel): new mission information

        Returns:
            bool: True of the mission_stac on disk must be updated by mission information
        """
        return os.path.exists(mission_stac.self_href) and len(
            mission_stac.description
        ) < len(mission.MISSION_INFORMATION.MISSION_DESC)

    def _update(self, mission_stac: pystac.Catalog, mission: MissionModel):
        """Update the STAC catalog with mission model.

        Args:
            mission_stac (pystac.Catalog): STAC catalog to update
            mission (MissionModel): New information
        """
        mission_stac_new = mission.create_stac_catalog(
            self.body_id, self.citations
        )
        mission_stac.title = mission_stac_new.title
        mission_stac.description = mission_stac_new.description
        mission_stac.stac_extensions = mission_stac_new.stac_extensions
        mission_stac.extra_fields = mission_stac_new.extra_fields
        mission_stac.save_object(include_self_link=False)

    def handle(self, request: Any) -> None:
        if isinstance(request, MissionModel):
            # Get the mission from the STAC catalog
            mission: MissionModel = request
            mission_stac = cast(
                pystac.Catalog,
                self.catalog.get_child(self.mission_id, recursive=True),
            )

            if not self._is_exists(mission_stac):
                # mission is not found, so create it
                stac_mission = mission.create_stac_catalog(
                    self.body_id, self.citations
                )

                # use mission_id of PDS collection to avoid interop problem
                stac_mission.id = self.mission_id

                # Get the parent of mission: the solar body
                body_cat = cast(
                    pystac.Catalog, self.catalog.get_child(self.body_id)
                )

                # Add the mission to the planet
                body_cat.add_child(stac_mission)
                logger.info(f"{stac_mission.id} added to {body_cat.id}")
            elif self._is_must_be_updated(mission_stac, mission):
                logger.info(f"{mission_stac.self_href} has been updated")
                self._update(mission_stac, mission)
        else:
            super().handle(request)


class PlateformHandler(AbstractHandler):
    """A handler for adding instrument host platforms to a STAC catalog.

    Attributes:
        catalog (pystac.Catalog): The root catalog to add platforms to.
        body_id (str): The ID of the celestial body the platforms are associated with.
        mission_id (str): The ID of the mission the platforms are associated with.
        citations (Optional[ReferencesModel]): An optional model of references to add to the platforms.
    """

    def __init__(
        self,
        catalog: pystac.Catalog,
        body_id: str,
        mission_id: str,
        citations: Optional[ReferencesModel],
    ):
        self.__catalog: pystac.Catalog = catalog
        self.__body_id: str = body_id
        self.__mission_id: str = mission_id
        self.__citations: Optional[ReferencesModel] = citations

    @property
    def catalog(self) -> pystac.Catalog:
        """Gets the pystac Catalog object associated with this handler.

        Returns:
            A pystac Catalog object.
        """
        return self.__catalog

    @property
    def body_id(self) -> str:
        """Gets the ID of the celestial body associated with this handler.

        Returns:
            A string containing the celestial body ID.
        """
        return self.__body_id

    @property
    def mission_id(self) -> str:
        """Gets the ID of the mission associated with this handler.

        Returns:
            A string containing the mission ID.
        """
        return self.__mission_id

    @property
    def citations(self) -> Optional[ReferencesModel]:
        """Gets the ReferencesModel object containing references for the mission and the platform.

        Returns:
            An optional ReferencesModel object.
        """
        return self.__citations

    def _is_must_be_updated(
        self, plateform_stac: pystac.Catalog, plateform: InstrumentHostModel
    ) -> bool:
        """Determines whether the STAC catalog for the platform must be updated.

        Args:
            plateform_stac: The pystac Catalog object associated with the platform.
            plateform: An InstrumentHostModel object representing the platform.

        Returns:
            A boolean value indicating whether the STAC catalog for the platform must be updated.
        """
        # Check if the STAC catalog for the platform exists and has a shorter description than
        # the one in the InstrumentHostModel object.
        return os.path.exists(plateform_stac.self_href) and len(
            plateform_stac.description
        ) < len(plateform.INSTRUMENT_HOST_INFORMATION.INSTRUMENT_HOST_DESC)

    def _update(
        self, plateform_stac: pystac.Catalog, plateform: InstrumentHostModel
    ):
        """Updates the STAC catalog for the platform.

        Args:
            plateform_stac: The pystac Catalog object associated with the platform.
            plateform: An InstrumentHostModel object representing the platform.
        """
        # Create a new STAC catalog for the platform using the InstrumentHostModel object.
        plateform_stac_new = plateform.create_stac_catalog(
            self.body_id, self.citations
        )

        # Update the STAC catalog for the platform with the information from the new catalog.
        plateform_stac.title = plateform_stac_new.title
        plateform_stac.description = plateform_stac_new.description
        plateform_stac.stac_extensions = plateform_stac_new.stac_extensions
        plateform_stac.extra_fields = plateform_stac_new.extra_fields
        plateform_stac.save_object(include_self_link=False)

    def _add_plateform_to_mission(self, plateform: InstrumentHostModel):
        """Adds a platform to the STAC catalog.

        Args:
            plateform (InstrumentHostModel): The platform to be added to the STAC catalog.
        """
        # Get the platform ID
        plateform_id: str = plateform.get_plateform_id()

        # Get the platform STAC catalog, if it exists
        plateform_stac = cast(
            pystac.Catalog,
            self.catalog.get_child(plateform_id, recursive=True),
        )

        # Check if the platform exists in the catalog
        if not self._is_exists(plateform_stac):
            # Get the mission STAC catalog
            stac_mission = cast(
                pystac.Catalog,
                self.catalog.get_child(self.mission_id, recursive=True),
            )
            logger.debug(f"Looking for {self.mission_id}: {stac_mission}")

            # Create a STAC catalog for the platform
            stac_plateform = plateform.create_stac_catalog(
                self.body_id, self.citations
            )

            # Add the platform STAC catalog as a child of the mission STAC catalog
            stac_mission.add_child(stac_plateform)
            logger.debug(f"{stac_plateform.id} added to {stac_mission.id}")
        elif self._is_must_be_updated(plateform_stac, plateform):
            logger.info(f"{plateform_stac.self_href} has been updated")
            self._update(plateform_stac, plateform)

    def _add_plateforms_to_mission(
        self, plateforms: List[InstrumentHostModel]
    ):
        """
        Adds a list of platforms to the STAC catalog.

        Args:
            plateforms (List[InstrumentHostModel]): The list of platforms to be added to the STAC catalog.
        """
        # Iterate over the list of platforms and add each platform to the mission STAC catalog

        for plateform in plateforms:
            self._add_plateform_to_mission(plateform)

    def handle(self, request: Any) -> None:
        """
        Handles the request to add platforms to the STAC catalog.

        Args:
            request (Any): The request to add platforms to the STAC catalog.
        """
        if isinstance(request, InstrumentHostModel):
            # If the request is a single platform, add it to the mission STAC catalog
            plateform: InstrumentHostModel = request
            self._add_plateform_to_mission(plateform)
        elif isinstance(request, list) and isinstance(
            request[0], InstrumentHostModel
        ):
            # If the request is a list of platforms, add all of them to the mission STAC catalog
            plateforms: List[InstrumentHostModel] = request
            self._add_plateforms_to_mission(plateforms)
        else:
            # If the request is neither a single platform nor a list of platforms, call the base class's handle method
            super().handle(request)


class InstrumentHandler(AbstractHandler):
    """A handler for adding instrument to a STAC catalog.

    Attributes:
        catalog (pystac.Catalog): The root catalog to add platforms to.
        body_id (str): The ID of the celestial body the platforms are associated with.
        citations (Optional[ReferencesModel]): An optional model of references to add to the platforms.
    """

    def __init__(
        self,
        catalog: pystac.Catalog,
        body_id: str,
        citations: Optional[ReferencesModel],
    ):
        """A class representing an Instrument handler that can add Instruments to a STAC catalog.

        Args:
            catalog (pystac.Catalog): A Catalog object representing the STAC catalog.
            body_id (str): The ID of the celestial body.
            citations (Optional[ReferencesModel]): A ReferencesModel object representing the citations for the mission.
        """
        self.__catalog: pystac.Catalog = catalog
        self.__body_id: str = body_id
        self.__citations: Optional[ReferencesModel] = citations

    @property
    def catalog(self) -> pystac.Catalog:
        """Get the STAC catalog."""
        return self.__catalog

    @property
    def body_id(self) -> str:
        """Get the ID of the solar body."""
        return self.__body_id

    @property
    def citations(self) -> Optional[ReferencesModel]:
        """Get the citations for the mission."""
        return self.__citations

    def _is_must_be_updated(
        self, instrument_stac: pystac.Catalog, instrument: InstrumentModel
    ) -> bool:
        """Check if the given STAC Catalog for the Instrument must be updated.

        Args:
            instrument_stac (pystac.Catalog): A Catalog object representing the STAC catalog for the Instrument.
            instrument (InstrumentModel): An InstrumentModel object representing the Instrument.

        Returns:
            bool: True if the given STAC Catalog for the Instrument must be updated, False otherwise.
        """
        return os.path.exists(instrument_stac.self_href) and len(
            instrument_stac.description
        ) < len(instrument.INSTRUMENT_INFORMATION.INSTRUMENT_DESC)

    def _update(
        self, instrument_stac: pystac.Catalog, instrument: InstrumentModel
    ):
        """Update the given STAC Catalog for the Instrument with the provided InstrumentModel.

        Args:
            instrument_stac (pystac.Catalog): A Catalog object representing the STAC catalog for the Instrument.
            instrument (InstrumentModel): An InstrumentModel object representing the Instrument.
        """
        instrument_stac_new = instrument.create_stac_catalog(
            self.body_id, self.citations
        )
        instrument_stac.title = instrument_stac_new.title
        instrument_stac.description = instrument_stac_new.description
        instrument_stac.stac_extensions = instrument_stac_new.stac_extensions
        instrument_stac.extra_fields = instrument_stac_new.extra_fields
        instrument_stac.save_object(include_self_link=False)

    def _add_instrument_to_mission(self, instrument: InstrumentModel):
        """Add an InstrumentModel to the STAC Catalog of the mission.

        Args:
            instrument (InstrumentModel): The InstrumentModel instance to add.
        """
        # Retrieve the ID of the instrument
        instrument_id: str = instrument.get_instrument_id()
        # Retrieve the STAC Catalog for this instrument
        instrument_stac = cast(
            pystac.Catalog,
            self.catalog.get_child(instrument_id, recursive=True),
        )
        # If the instrument doesn't exist yet in the Catalog, create it
        if not self._is_exists(instrument_stac):
            # Retrieve the ID of the platform on which the instrument is mounted
            plateform_id: str = instrument.get_plateform_id()

            # Retrieve the STAC Catalog for this platform
            stac_plateform = cast(
                pystac.Catalog,
                self.catalog.get_child(plateform_id, recursive=True),
            )
            logger.debug(f"Looking for {plateform_id}: {stac_plateform}")

            # Create the STAC Catalog for the instrument
            stac_instrument = instrument.create_stac_catalog(
                self.body_id, self.citations
            )

            # Add the instrument Catalog to the platform Catalog
            stac_plateform.add_child(stac_instrument)
            logger.debug(f"{stac_instrument.id} added to {stac_plateform.id}")
        elif self._is_must_be_updated(instrument_stac, instrument):
            # If the instrument already exists in the Catalog, check if it needs to be updated
            logger.info(f"{instrument_stac.self_href} has been updated")
            self._update(instrument_stac, instrument)

    def _add_instruments_to_mission(self, instruments: List[InstrumentModel]):
        """Add multiple InstrumentModel instances to the STAC Catalog of the mission.

        Args:
            instruments (List[InstrumentModel]): A list of InstrumentModel instances to add.
        """
        # Iterate over each InstrumentModel instance and add them to the Catalog
        for instrument in instruments:
            self._add_instrument_to_mission(instrument)

    def handle(self, request: Any) -> None:
        """Handle the request to add an InstrumentModel or multiple InstrumentModel instances to the mission.

        Args:
            request (Any): The request object.
        """
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
    """A handler for adding collection to a STAC catalog.

    Attributes:
        catalog (pystac.Catalog): The root catalog to add platforms to.
        body_id (str): The ID of the celestial body the platforms are associated with.
        citations (Optional[ReferencesModel]): An optional model of references to add to the platforms.
        data_supplier (Optional[DataSupplierModel]): An optional model of data supplier to add to the platforms.
        data_producer (Optional[DataProducerModel]): An optional model of data producer to add to the platforms.
    """

    def __init__(
        self,
        catalog: pystac.Catalog,
        body_id: str,
        volume_desc: VolumeModel,
        citations: Optional[ReferencesModel],
    ):
        """Initializes DatasetHandler.

        Args:
            catalog: The root catalog to add collections to.
            body_id: The ID of the celestial body the collections are associated with.
            volume_desc: A model of the volume description for the collections.
            citations: An optional model of references to add to the collections.
        """
        self.__catalog: pystac.Catalog = catalog
        self.__body_id: str = body_id
        self.__citations: Optional[ReferencesModel] = citations
        self.__data_supplier: Optional[
            DataSupplierModel
        ] = volume_desc.DATA_SUPPLIER
        self.__data_producer: DataProducerModel = volume_desc.DATA_PRODUCER

    @property
    def catalog(self) -> pystac.Catalog:
        """pystac.Catalog: The root catalog to add collections to."""
        return self.__catalog

    @property
    def body_id(self) -> str:
        """The ID of the celestial body,  the collections are associated with."""
        return self.__body_id

    @property
    def data_supplier(self) -> Optional[DataSupplierModel]:
        """A model of the data supplier for the collections."""
        return self.__data_supplier

    @property
    def data_producer(self) -> DataProducerModel:
        """A model of the data producer for the collections."""
        return self.__data_producer

    @property
    def citations(self) -> Optional[ReferencesModel]:
        """A model of references to add to the collections."""
        return self.__citations

    def _is_must_be_updated(
        self, dataset_stac: pystac.Collection, dataset: DataSetModel
    ) -> bool:
        """Check whether a dataset in the catalog must be updated based on its description.

        Args:
            dataset_stac: A pystac Collection object representing the dataset.
            dataset: A DataSetModel object representing the dataset.

        Returns:
            True if the dataset's description has changed and the dataset must be updated, False otherwise.
        """
        # Get the description of the dataset from its DATA_SET_INFORMATION object
        description: Optional[
            str
        ] = dataset.DATA_SET_INFORMATION._get_description()
        # Check if the STAC collection already exists and if the dataset's description is longer than the existing one
        return (
            os.path.exists(dataset_stac.self_href)
            and description is not None
            and len(dataset_stac.description) < len(description)
        )

    def _update(self, dataset_stac: pystac.Collection, dataset: DataSetModel):
        """
        Update a dataset in the catalog with new metadata.

        Args:
            dataset_stac: A pystac Collection object representing the dataset to be updated.
            dataset: A DataSetModel object representing the new metadata for the dataset.
        """
        # Create a new STAC collection for the dataset
        dataset_stac_new = dataset.create_stac_collection(
            self.body_id,
            self.citations,
            self.data_supplier,
            self.data_producer,
        )

        # Update the existing STAC collection with the new information
        dataset_stac.title = dataset_stac_new.title
        dataset_stac.description = dataset_stac_new.description
        dataset_stac.stac_extensions = dataset_stac_new.stac_extensions
        dataset_stac.extra_fields = dataset_stac_new.extra_fields
        dataset_stac.save_object(include_self_link=False)

    def _add_dataset_to_instrument(self, dataset: DataSetModel):
        """
        Add a dataset to the appropriate instrument catalog in the overall catalog.

        Args:
            dataset: A DataSetModel object representing the dataset to be added.
        """
        # Get the ID of the dataset's STAC collection
        dataset_id: str = dataset.get_collection_id()

        # Get the existing STAC collection for the dataset (if it exists)
        dataset_stac = cast(
            pystac.Collection,
            self.catalog.get_child(dataset_id, recursive=True),
        )

        # If the dataset doesn't exist in the catalog, create a new STAC collection for it and add it to the appropriate instrument(s)
        if not self._is_exists(dataset_stac):
            stac_dataset = dataset.create_stac_collection(
                self.body_id,
                self.citations,
                self.data_supplier,
                self.data_producer,
            )
            # Get the ID(s) of the instrument(s) associated with the dataset
            instrument_ids: Union[
                str, List[str]
            ] = dataset.DATA_SET_HOST.get_instrument_id()

            # If there is only one instrument ID, add the dataset to that instrument's catalog
            if isinstance(instrument_ids, str):
                instrument_id: str = cast(str, instrument_ids)
                stac_instrument = cast(
                    pystac.Catalog,
                    self.catalog.get_child(instrument_id, recursive=True),
                )
                logger.debug(f"Looking for {instrument_id}: {stac_instrument}")
                stac_instrument.add_child(stac_dataset)
                logger.debug(
                    f"{stac_dataset.id} added to {stac_instrument.id}"
                )

            # If there are multiple instrument IDs, add the dataset to each instrument's catalog
            else:
                for instrument_id in instrument_ids:
                    stac_instrument = cast(
                        pystac.Catalog,
                        self.catalog.get_child(instrument_id, recursive=True),
                    )
                    logger.debug(
                        f"Looking for {instrument_id}: {stac_instrument}"
                    )
                    stac_instrument.add_child(stac_dataset)
                    logger.debug(
                        f"{stac_dataset.id} added to {stac_instrument.id}"
                    )

        # If the dataset already exists in the catalog and needs to be updated, update it
        elif self._is_must_be_updated(dataset_stac, dataset):
            logger.info(f"{dataset_stac.self_href} has been updated")
            self._update(dataset_stac, dataset)

    def _add_datasets_to_instrument(self, datasets: List[DataSetModel]):
        """Add multiple DataSetModel instances to the STAC Catalog of the instrument.

        Args:
            datasets (List[DataSetModel]): A list of DataSetModel instances to add.
        """
        # Iterate over each DataSetModel instance and add them to the Catalog
        for dataset in datasets:
            self._add_dataset_to_instrument(dataset)

    def handle(self, request: Any) -> None:
        """Handle the request to add an DataSetModel or multiple DataSetModel instances to the instrument.

        Args:
            request (Any): The request object.
        """
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
    # Dictionary that defines the sort order of PDS catalog files
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
        # Initializes the class with a root STAC catalog
        self.__root_stac: pystac.Catalog = root_stac
        self.__catalogs: Dict[str, Any] = dict()

    def _is_already_exists(self, id: str) -> bool:
        """Checks if the catalog or collection ID is in the STAC catalog

        Args:
            id (str): catalog or collection ID

        Returns:
            bool: True when the catalog or collection ID is in the STAC catalog
        """
        # Returns a boolean indicating if a catalog or collection ID exists in the STAC catalog
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
        if volume_desc is None:
            # If volume description is not available, return
            return

        # Get the body ID and mission ID from the PDS collection
        body_id: str = pds_collection.get_body_id()
        mission_id: str = pds_collection.get_mission_id()

        if not self._is_already_exists(body_id):
            # If body catalog does not exist, create it and add it to the root catalog
            pystac_body_cat = pds_collection.create_stac_body_catalog()
            self.root_stac.add_child(pystac_body_cat)

        mission = MissionHandler(
            self.root_stac, body_id, mission_id, citations
        )
        plateform = PlateformHandler(
            self.root_stac, body_id, mission_id, citations
        )
        instrument = InstrumentHandler(self.root_stac, body_id, citations)
        dataset = DatasetHandler(
            self.root_stac, body_id, volume_desc, citations
        )
        mission.set_next(plateform).set_next(instrument).set_next(dataset)

        catalogs = list(self.catalogs.keys())
        catalogs.sort(key=lambda val: StacPdsCollection.SORT_ORDER[val])
        for catalog_name in catalogs:
            logger.info(f"\tSTAC transformation of {catalog_name}")
            catalog = self.catalogs[catalog_name]
            mission.handle(catalog)
