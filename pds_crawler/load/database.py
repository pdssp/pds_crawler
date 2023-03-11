# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Module Name:
    database

Description:
    The database module provides capabilities to store and load the PDS insformation.
    The stored information comes from the models:
    - PdsRegistryModel : collection information
    - List[str] : list of precomputed URL to download all PDS data from ODE webservice
    - ...

Classes:
    Database :
        Database implementation
    StacStorage:
        Storage for STAC
    PdsStorage:
        PDS storage
    PdsCollectionStorage
        PDS collection storage


.. uml::

    class Database {
        - __base_directory: str
        - __pds_dir: str
        - __stac_dir: str
        - __hdf5_name: str
        - __stac_storage: StacStorage
        - __pds_storage: PdsStorage
        - __hdf5_storage: Hdf5Storage

        + base_directory: str
        + pds_dir: str
        + stac_dir: str
        + hdf5_name: str
        + stac_storage: StacStorage
        + pds_storage: PdsStorage
        + hdf5_storage: Hdf5Storage

        + __init__(base_directory: str) -> None
        + init_storage() -> None
        + reset_storage() -> None
        + __repr__() -> str
    }

    class PdsCollectionStorage {
        - __directory: str
        +__init__(self, directory: str) -> None
        + directory: str
        + list_files() : List[str]
        + get_volume_description() : VolumeModel
        + list_catalogs() : Dict[str, Any]
        + get_catalog(file: str, catalogue_type: PdsParserFactory.FileGrammary) : Any
        + download(urls: List[str], nb_workers: int = 3, timeout: int = 180, time_sleep: int = 1) -> None
        + __repr__() : str
    }

    class PdsStorage{
        + __init__(base_directory: str) -> None
        -__directory: str
        +init_storage_directory()
        +reset_storage()
        +get_pds_storage_for(pds_collection: PdsRegistryModel) -> PdsCollectionStorage
        +directory: str
        +__repr__() -> str
    }

    class Hdf5Storage{
        - HDF_SEP: str = "/"
        - DS_URLS: str = "urls"
        - __name
        + name
        + init_storage(name:str)
        + reset_storage()
        - _has_changed(store_db:Any, pds_collection:PdsRegistryModel):bool
        - _has_attribute_in_group(node:Any):bool
        - _save_collection(pds_collection:PdsRegistryModel, f:Any):bool
        - _read_and_convert_attributes(node:Any):Dict[str,Any]
        - _save_urls_in_new_dataset(self, pds_collection: PdsRegistryModel, urls: List[str])
        - _save_urls_in_existing_dataset(self, pds_collection: PdsRegistryModel, urls: List[str])
        + save_collection(pds_collection:PdsRegistryModel): bool
        + save_collections(collections_pds:List[PdsRegistryModel]): bool
        + load_collections(body:Optional[str]=None, dataset_id:Optional[str]=None):List[PdsRegistryModel]
        + save_urls(pds_collection: PdsRegistryModel, urls: List[str])
        + load_urls(pds_collection: PdsRegistryModel) -> List[str]
        + static define_group_from(words: List[str]) -> str
    }

    class StacStorage {
        -__directory: str
        -__root_catalog: pystac.Catalog
        -__layout: LargeDataVolumeStrategy
        +directory: str
        +root_catalog: pystac.Catalog
        +__init__(directory: str)
        -_load_root_catalog()
        +init_storage_directory()
        +reset_storage()
        +refresh()
        +item_exists(record: PdsRecordModel) -> bool
        +catalog_normalize_and_save()
        +root_normalize_and_save(catalog: pystac.Catalog)
        +normalize_and_save(cat_or_coll: Union[pystac.Collection, pystac.Catalog])
        +__repr__() -> str
    }

    Database *-- PdsStorage
    Database *-- Hdf5Storage
    Database *-- StacStorage
    PdsStorage *-- PdsCollectionStorage

Author:
    Jean-Christophe Malapert
"""
import logging
import os
import re
import shutil
from typing import Any
from typing import cast
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import h5py
import numpy as np
import pystac

from ..models import PdsRecordModel
from ..models import PdsRegistryModel
from ..models import VolumeModel
from ..utils import parallel_requests
from ..utils import UtilsMonitoring
from .pds_objects_parser import PdsParserFactory
from .strategy import LargeDataVolumeStrategy

logger = logging.getLogger(__name__)


class StacStorage:
    """STAC storage."""

    def __init__(self, directory: str):
        """initializes several private properties, including a pystac.Catalog
        object representing the root catalog.

        Args:
            directory (str): base directory
        """
        self.__directory = directory
        self.__layout = LargeDataVolumeStrategy()
        logger.debug(
            f"[StacStorage] Initialize StacDorage with diretory={self.__directory}"
        )
        self.init_storage_directory()
        self._load_root_catalog()

    @property
    def directory(self) -> str:
        """Returns the directory path.

        Returns:
            str: the directory path
        """
        return self.__directory

    @property
    def root_catalog(self) -> Optional[pystac.Catalog]:
        """Returns the root catalog as a pystac.Catalog object.

        Returns:
            Optional[pystac.Catalog]: the root catalog as a pystac.Catalog object
        """
        return self.__root_catalog

    def _load_root_catalog(self):
        """Load root STAC catalog"""
        try:
            self.__root_catalog = pystac.Catalog.from_file(
                os.path.join(self.directory, "catalog.json")
            )
            logger.debug("[StacStorage] root_catalog found")
        except FileNotFoundError:
            self.__root_catalog = None
            logger.debug("[StacStorage] root_catalog not found, create one")
            self.__root_catalog = pystac.Catalog(
                id="urn:pdssp:pds",
                title="Planetary Data System",
                description="Georeferenced data extracted from ode.rsl.wustl.edu",
            )
            self.__root_catalog.add_link(
                pystac.Link(
                    rel=pystac.RelType.PREVIEW,
                    target="https://pdsmgmt.gsfc.nasa.gov/images/PDS_Logo.png",
                    title="PDS logo",
                    media_type=pystac.MediaType.PNG,
                )
            )
            self.root_normalize_and_save(self.__root_catalog)

    def init_storage_directory(self):
        """Creates the storage directory if it doesn't exist."""
        os.makedirs(self.directory, exist_ok=True)

    def reset_storage(self):
        """Removes the storage directory and all its contents."""
        shutil.rmtree(self.directory)

    def refresh(self):
        """Reloads the root catalog from the catalog.json file."""
        self._load_root_catalog()

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def item_exists(self, record: PdsRecordModel) -> bool:
        """Returns True if an item (represented by a PdsRecordModel object) exists in
        the storage directory, otherwise False.

        Args:
            record (PdsRecordModel): item

        Returns:
            bool: True if an item (represented by a PdsRecordModel object) exists in
            the storage directory, otherwise False
        """
        directory: str = os.path.join(
            self.directory,
            record.get_body_id(),
            record.get_mission_id(),
            record.get_plateform_id(),
            record.get_instrument_id(),
            record.get_collection_id(),
            record.get_id(),
        )
        logger.debug(f"[StacStorage] item_exists in {directory}")
        return os.path.exists(directory)

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def catalog_normalize_and_save(self):
        """Normalizes the root catalog and saves it to disk."""
        if self.root_catalog is None:
            logger.debug(
                "[StacStorage] catalog_normalize_and_save - root_catalog not found"
            )
            self.refresh()
        if self.root_catalog is None:
            logger.debug(
                "[StacStorage] catalog_normalize_and_save - root_catalog not found"
            )
            raise ValueError("Cannot load STAC root")
        self.root_catalog.normalize_and_save(
            self.directory,
            catalog_type=pystac.CatalogType.SELF_CONTAINED,
            strategy=self.__layout.get_strategy(),
        )

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def root_normalize_and_save(self, catalog: pystac.Catalog):
        """Normalizes the given catalog and saves it to disk using the root
        directory as the output directory."""
        catalog.normalize_and_save(
            self.directory,
            catalog_type=pystac.CatalogType.SELF_CONTAINED,
            strategy=self.__layout.get_strategy(),
        )

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def normalize_and_save(
        self, cat_or_coll: Union[pystac.Collection, pystac.Catalog]
    ):
        """Normalizes the given catalog or collection and saves it to disk."""
        cat_or_coll.normalize_hrefs(
            cat_or_coll.self_href,
            strategy=self.__layout.get_strategy(),
        )
        cat_or_coll.save()

    def __repr__(self) -> str:
        """Returns a string representation of the StacStorage object.

        Returns:
            str: a string representation of the StacStorage object.
        """
        return f"StacStorage({self.directory})"


class PdsCollectionStorage:
    """Storage for a Planetary Data System (PDS) collection.."""

    def __init__(self, directory: str):
        """Initializes the class instance with the provided directory string argument.

        This directory is created if it does not already exist.

        Args:
            directory (str): diretory
        """
        self.__directory = directory
        os.makedirs(directory, exist_ok=True)

    @property
    def directory(self) -> str:
        """Returns the directory path.

        Returns:
            str: the directory path
        """
        return self.__directory

    def list_files(self) -> List[str]:
        """Returns a list of filenames in the directory that are regular files.

        Returns:
            List[str]: list of filenames
        """
        files = os.listdir(self.directory)
        return [
            f for f in files if os.path.isfile(os.path.join(self.directory, f))
        ]

    def list_records_files(self) -> List[str]:
        """Returns a list of filenames in the directory that are regular files coming from PdsRecordsWs.

        Returns:
            List[str]: list of filenames
        """
        files = os.listdir(self.directory)
        return [
            f
            for f in files
            if os.path.isfile(os.path.join(self.directory, f))
            and f.endswith(".json")
        ]

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def get_volume_description(self) -> VolumeModel:
        """Returns a VolumeModel object containing the parsed contents of the "voldesc.cat" file in the directory

        Returns:
            VolumeModel: Voldesc.cat object
        """
        voldesc: str = os.path.join(self.directory, "voldesc.cat")
        return PdsParserFactory.parse(
            voldesc, PdsParserFactory.FileGrammary.VOL_DESC
        )

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def list_catalogs(self) -> Dict[str, Any]:
        """Returns a dictionary containing the contents of the CATALOG object
        in the VolumeModel returned by get_volume_description

        Returns:
            Dict[str, Any]: a dictionary containing the contents of the CATALOG
            object in the VolumeModel
        """
        volume: VolumeModel = self.get_volume_description()
        return {
            key: volume.CATALOG.__dict__[key]
            for key in volume.CATALOG.__dict__.keys()
        }

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def get_catalog(
        self, file: str, catalogue_type: PdsParserFactory.FileGrammary
    ) -> Any:
        """Returns the parsed contents of a PDS catalogue file specified by
        the file argument, using the catalogue_type argument to specify the
        type of catalogue parser to use.

        Args:
            file (str): PDS catalog
            catalogue_type (PdsParserFactory.FileGrammary): Information about the catalog

        Returns:
            Any: the parsed contents of a PDS catalogue file
        """
        filename: str = os.path.join(self.directory, file.lower())
        return PdsParserFactory.parse(filename, catalogue_type)

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def download(
        self,
        urls: List[str],
        nb_workers: int = 3,
        timeout: int = 180,
        time_sleep: int = 1,
        progress_bar: bool = True,
    ):
        """Download URLs in parallel in the collection storage.

        Args:
            urls (List[str]): List of URLs to download
            nb_workers (int, optional): nb workers. Defaults to 3.
            timeout (int, optional): timeout in seconds. Defaults to 180
            time_sleep (int, optional): sleep. Defaults to 1.
            progress_bar (bool, optional): Set progress_bar. Defaults to True.
        """
        parallel_requests(
            self.directory,
            urls,
            nb_workers=nb_workers,
            timeout=timeout,
            time_sleep=time_sleep,
            progress_bar=progress_bar,
        )

    def __repr__(self) -> str:
        """Returns a string representation of the class instance."""
        return f"PdsCollectionStorage({self.directory})"


class PdsStorage:
    """Main PDS storage."""

    def __init__(self, directory: str):
        self.__directory: str = directory
        self.init_storage_directory()

    def init_storage_directory(self):
        os.makedirs(self.directory, exist_ok=True)

    def reset_storage(self):
        shutil.rmtree(self.directory)

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def get_pds_storage_for(
        self, pds_collection: PdsRegistryModel
    ) -> PdsCollectionStorage:
        relative_dir: str = Hdf5Storage.define_group_from(
            [
                pds_collection.ODEMetaDB,
                pds_collection.IHID,
                pds_collection.IID,
                pds_collection.PT,
                pds_collection.DataSetId,
            ]
        )
        directory = os.path.join(self.directory, relative_dir)
        return PdsCollectionStorage(directory)

    @property
    def directory(self) -> str:
        return self.__directory

    def __repr__(self) -> str:
        return f"PdsStorage({self.directory})"


class Hdf5Storage:
    HDF_SEP: str = "/"
    DS_URLS: str = "urls"

    def __init__(self, name: str):
        self.__name = name
        self.init_storage(self.__name)

    @property
    def name(self):
        return self.__name

    def init_storage(self, name: str):
        with h5py.File(name, "a") as f:
            if "metadata" not in f:
                metadata = f.create_group("metadata")
                metadata.attrs["author"] = "Jean-Christophe Malapert"

    def reset_storage(self):
        os.remove(self.name)

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def _has_changed(
        self, store_db: Any, pds_collection: PdsRegistryModel
    ) -> bool:
        """Check if the same version of the PDS collection has already been stored.

        To check the if the version is an update or not, the comparison is performed based on
        the number of products and the existing keywords `NumberProducts` in store_db.

        Args:
            store_db (Any): node in HDF5
            pds_collection (PdsRegistryModel): PDS collection

        Returns:
            bool: True when the collection is new or must be updated otherwise False
        """
        return not (
            "NumberProducts" in store_db.attrs
            and pds_collection.NumberProducts
            == store_db.attrs["NumberProducts"]
        )

    def _has_attribute_in_group(self, node: Any) -> bool:
        """Check if it exists attributes in the node.

        Args:
            node (Any): the HDF5 node

        Returns:
            bool: True when both the node is a h5py.Group and node has attributes
        """
        return isinstance(node, h5py.Group) and node.attrs  # type: ignore

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def _save_collection(
        self, pds_collection: PdsRegistryModel, f: Any
    ) -> bool:
        is_saved: bool
        group_path: str = Hdf5Storage.define_group_from(
            [
                pds_collection.ODEMetaDB,
                pds_collection.IHID,
                pds_collection.IID,
                pds_collection.PT,
                pds_collection.DataSetId,
            ]
        )
        store_hdf = f.get(group_path, None)
        if store_hdf is None:
            logger.debug(
                "[StacStorage] _save_collection - store_hdf does not exist"
            )
            store_hdf = f.create_group(group_path)
            pds_collection.to_hdf5(store_hdf)
            is_saved = True
        elif self._has_changed(store_hdf, pds_collection):
            logger.info("[StacStorage] _save_collection - Update HDF5")
            pds_collection.to_hdf5(store_hdf)
            is_saved = True
        else:
            logger.warning(
                f"{pds_collection} has not changed, skip the record in the database"
            )
            is_saved = False
        return is_saved

    def _read_and_convert_attributes(self, node: Any) -> Dict[str, Any]:
        """Read and converts convert attributs.

        Args:
            node (Any): HDF5 group or dataset

        Returns:
            Dict[str, Any]: attributs as dictionary
        """
        group_attributes = dict(node.attrs)
        for key in group_attributes.keys():
            if isinstance(group_attributes[key], np.bytes_):
                group_attributes[key] = eval(
                    group_attributes[key].decode("utf-8")
                )
        return group_attributes

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def save_collection(self, pds_collection: PdsRegistryModel) -> bool:
        """Save the PDS collection in the database.

        Args:
            pds_collection (PdsRegistryModel): the PDS collection

        Returns:
            bool: True is the collection is saved otherwise False
        """
        is_saved: bool
        with h5py.File(self.name, "a") as f:
            is_saved = self._save_collection(pds_collection, f)
        return is_saved

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def save_collections(
        self, collections_pds: List[PdsRegistryModel]
    ) -> bool:
        """Save all the PDS collections in the database.

        Args:
            collections_pds (List[PdsRegistryModel]): the collections.

        Returns:
            bool: True is the collection is saved otherwise False
        """
        is_saved = True
        with h5py.File(self.name, "a") as f:
            for pds_collection in collections_pds:
                is_saved = is_saved & self._save_collection(pds_collection, f)
        return is_saved

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def load_collections(
        self, body: Optional[str] = None, dataset_id: Optional[str] = None
    ) -> List[PdsRegistryModel]:
        """Load all collections metadata from the database.

        Args:
            body (Optional[str]): name of the body to get. Defaults to None
            dataset_id (Optional[str]): Dataset ID , used to filtr the collection. Defaults to None

        Returns:
            List[PdsRegistryModel]: All PDS collections metadata
        """
        pds_collections: List[PdsRegistryModel] = list()

        def extract_attributes(name: str, node: Any):
            if name != "metadata" and self._has_attribute_in_group(node):
                dico: Dict[str, Any] = self._read_and_convert_attributes(node)
                pds_collections.append(PdsRegistryModel.from_dict(dico))

        with h5py.File(self.name, "r") as f:
            f.visititems(extract_attributes)

        # filter pds_collection by body name
        pds_registry_models = [
            pds_registry_model
            for pds_registry_model in pds_collections
            if body is None
            or pds_registry_model.get_body().upper() == body.upper()
        ]

        # filter pds_collections by dataset ID
        pds_registry_model = [
            pds_registry_model
            for pds_registry_model in pds_registry_models
            if dataset_id is None
            or pds_registry_model.DataSetId.upper() == dataset_id.upper()
        ]

        return pds_registry_model

    def _save_urls_in_new_dataset(
        self, pds_collection: PdsRegistryModel, urls: List[str]
    ):
        """Save URLS in a new dataset, which is represented by pds_collection

        Args:
            pds_collection (PdsRegistryModel): PDS collection, used to define the name of the dataset
            urls (List[str]): URLs to save
        """
        with h5py.File(self.name, mode="a") as f:
            group_path: str = Hdf5Storage.define_group_from(
                [
                    pds_collection.ODEMetaDB.lower(),
                    pds_collection.IHID,
                    pds_collection.IID,
                    pds_collection.PT,
                    pds_collection.DataSetId,
                ]
            )
            dset = f.create_dataset(
                group_path + Hdf5Storage.HDF_SEP + Hdf5Storage.DS_URLS,
                (len(urls),),
                dtype=h5py.special_dtype(vlen=str),
            )
            dset[:] = urls
            logger.info(f"Writing {len(urls)} URLs in hdf5:{group_path}/urls")

    def _save_urls_in_existing_dataset(
        self, pds_collection: PdsRegistryModel, urls: List[str]
    ):
        """Save URLs in existing dataset, which is represented by pds_collection

        Args:
            pds_collection (PdsRegistryModel): PDS collections used to define the name of the dataset to load
            urls (List[str]): urls to save
        """
        with h5py.File(self.name, mode="r+") as f:
            group_path: str = Hdf5Storage.define_group_from(
                [
                    pds_collection.ODEMetaDB.lower(),
                    pds_collection.IHID,
                    pds_collection.IID,
                    pds_collection.PT,
                    pds_collection.DataSetId,
                ]
            )
            dset_name: str = (
                group_path + Hdf5Storage.HDF_SEP + Hdf5Storage.DS_URLS
            )
            dset: h5py.Dataset = cast(h5py.Dataset, f[dset_name])

            # Update the Urls
            dset.resize(len(urls), axis=0)
            dset[:] = urls

            # Write the changes on the disk
            dset.write_direct(urls, source_sel=np.s_[:])
            logger.info(f"Writing {len(urls)} URLs in hdf5:{group_path}/urls")

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def save_urls(self, pds_collection: PdsRegistryModel, urls: List[str]):
        """Save URLs in the "urls" dataset in a given group where the group name is built from pds_collection.
        The dataset can be an existing dataset or a new one

        Args:
            pds_collection (PdsRegistryModel): PDS collection
            urls (List[str]): all pregenerated url to download the data
        """
        old_urls: List[str] = self.load_urls(pds_collection)
        if len(old_urls) == 0:
            self._save_urls_in_new_dataset(pds_collection, urls)
        elif sorted(urls) == sorted(old_urls):
            logger.debug(
                f"These urls {urls} are already stored for {pds_collection}, skip to save the URLs dataset"
            )
        else:
            logger.info(
                f"""
            Updates the Urls in dataset for {pds_collection}:
                old_urls: {sorted(old_urls)}
                new_urls: {sorted(urls)}
            """
            )
            self._save_urls_in_existing_dataset(pds_collection, urls)

    @UtilsMonitoring.io_display(level=logging.DEBUG)
    def load_urls(self, pds_collection: PdsRegistryModel) -> List[str]:
        """Loads pregenerated URLs for a given PDS collection.

        Args:
            pds_collection (PdsRegistryModel): PDS collection

        Returns:
            List[str]: List of URLs
        """
        urls: List[str] = list()
        with h5py.File(self.name, "r") as f:
            group_path: str = Hdf5Storage.define_group_from(
                [
                    pds_collection.ODEMetaDB.lower(),
                    pds_collection.IHID,
                    pds_collection.IID,
                    pds_collection.PT,
                    pds_collection.DataSetId,
                ]
            )
            dset = f.get(
                group_path + Hdf5Storage.HDF_SEP + Hdf5Storage.DS_URLS, None
            )
            if dset is not None:
                urls = [item.decode("utf-8") for item in list(dset)]  # type: ignore
        return urls

    @staticmethod
    def define_group_from(words: List[str]) -> str:
        """Create a valid name for HDF5 node based on words.

        Args:
            words (List[str]): Words

        Returns:
            str: Valid name for HDF5 node
        """
        return Hdf5Storage.HDF_SEP.join(
            [re.sub(r"[^a-zA-Z0-9_]", "_", word) for word in words]
        )

    def __repr__(self) -> str:
        return f"Hdf5({self.name})"


class Database:
    """Provides the database implementation using a HDF5 file."""

    PDS_STORAGE_DIR = "files"
    STAC_STORAGE_DIR = "stac"
    HDF5_STORAGE_NAME = "pds.h5"

    def __init__(self, base_directory: str) -> None:
        self.__base_directory = base_directory
        self.__pds_dir: str = Database.PDS_STORAGE_DIR
        self.__stac_dir: str = Database.STAC_STORAGE_DIR
        self.__hdf5_name: str = Database.HDF5_STORAGE_NAME
        self.init_storage()

        logger.debug(
            f"""
            Path to the database : {base_directory}
            Path to HDF5 STorage : {self.hdf5_storage}
            Path to PDS Storage : {self.pds_storage}
            Path to STAC Storage: {self.stac_storage}"""
        )

    @property
    def base_directory(self) -> str:
        return self.__base_directory

    @property
    def pds_dir(self) -> str:
        return self.__pds_dir

    @pds_dir.setter
    def pds_dir(self, value: str):
        self.__pds_dir = value

    @property
    def stac_dir(self) -> str:
        return self.__stac_dir

    @stac_dir.setter
    def stac_dir(self, value: str):
        self.__stac_dir = value

    @property
    def hdf5_name(self) -> str:
        return self.__hdf5_name

    @hdf5_name.setter
    def hdf5_name(self, value: str):
        self.__hdf5_name = value

    @property
    def stac_storage(self) -> StacStorage:
        return self.__stac_storage

    @property
    def pds_storage(self) -> PdsStorage:
        return self.__pds_storage

    @property
    def hdf5_storage(self) -> Hdf5Storage:
        return self.__hdf5_storage

    def init_storage(self):
        os.makedirs(self.base_directory, exist_ok=True)
        files_directory = os.path.join(self.base_directory, self.pds_dir)
        stac_directory = os.path.join(self.base_directory, self.stac_dir)
        hdf5_file = os.path.join(self.base_directory, self.hdf5_name)
        self.__stac_storage = StacStorage(stac_directory)
        self.__pds_storage = PdsStorage(files_directory)
        self.__hdf5_storage = Hdf5Storage(hdf5_file)

    def reset_storage(self):
        self.stac_storage.reset_storage()
        self.pds_storage.reset_storage()
        self.hdf5_storage.reset_storage()

    def __repr__(self) -> str:
        return f"Database({self.base_directory}, {self.hdf5_storage}, {self.pds_storage}, {self.stac_storage})"
