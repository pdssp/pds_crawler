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

Author:
    Jean-Christophe Malapert
"""
import logging
import os
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List

import h5py
import numpy as np

from ..models import PdsRegistryModel
from ..models import VolumeModel
from .pds_objects import PdsParserFactory

logger = logging.getLogger(__name__)


class StorageCollectionDirectory:
    def __init__(
        self, files_base_directory: str, pds_collection: PdsRegistryModel
    ):
        self.__files_base_directory: str = files_base_directory
        self.__pds_collection: str = pds_collection
        self._init_storage_directory()

    def _init_storage_directory(self):
        relative_dir: str = Database.define_group_from(
            [
                self.pds_collection.ODEMetaDB,
                self.pds_collection.IHID,
                self.pds_collection.IID,
                self.pds_collection.PT,
                self.pds_collection.DataSetId,
            ]
        )
        self.__directory = os.path.join(
            self.files_base_directory, relative_dir
        )
        os.makedirs(self.__directory, exist_ok=True)

    @property
    def pds_collection(self) -> PdsRegistryModel:
        return self.__pds_collection

    @property
    def files_base_directory(self) -> str:
        return self.__files_base_directory

    @property
    def directory(self) -> str:
        return self.__directory

    def list_files(self) -> List[str]:
        files = os.listdir(self.directory)
        return [
            f for f in files if os.path.isfile(os.path.join(self.directory, f))
        ]

    def get_volume_description(self) -> VolumeModel:
        voldesc: str = os.path.join(self.directory, "voldesc.cat")
        return PdsParserFactory.parse(
            voldesc, PdsParserFactory.FileGrammary.VOL_DESC
        )

    def list_catalogs(self) -> Dict[str, str]:
        volume: VolumeModel = self.get_volume_description()
        return {
            key: volume.CATALOG.__dict__[key]
            for key in volume.CATALOG.__dict__.keys()
        }

    def get_catalog(
        self, file: str, catalogue_type: PdsParserFactory.FileGrammary
    ) -> Any:
        filename: str = os.path.join(self.directory, file.lower())
        return PdsParserFactory.parse(filename, catalogue_type)


class Database:
    """Provides the database implementation using a HDF5 file."""

    HDF_SEP: str = "/"
    DS_URLS: str = "urls"

    def __init__(self, name: str) -> None:
        self.__name = name
        self.__base_directory = os.path.dirname(os.path.abspath(self.name))
        self.__files_base_directory = os.path.join(
            self.__base_directory, "files"
        )
        self.__stac_directory = os.path.join(self.__base_directory, "stac")
        logger.debug(
            f"""
            Path to the database : {name}
            Path to files : {self.__files_base_directory}
            Path to STAC : {self.__stac_directory}"""
        )
        self.create_directories()

    def create_directories(self):
        if not os.path.isdir(self.base_directory):
            os.makedirs(self.base_directory, exist_ok=True)
        if not os.path.isdir(self.files_base_directory):
            os.makedirs(self.files_base_directory, exist_ok=True)
        if not os.path.isdir(self.stac_directory):
            os.makedirs(self.stac_directory, exist_ok=True)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def base_directory(self) -> str:
        return self.__base_directory

    @property
    def files_base_directory(self) -> str:
        return self.__files_base_directory

    @property
    def stac_directory(self) -> str:
        return self.__stac_directory

    def _save_information(
        self, store_db: Any, pds_collection: PdsRegistryModel
    ):
        """Saves the information in the attributes of a HDF5 node

        Args:
            store_db (Any): HDF5 node
            pds_collection (PdsRegistryModel): PDS collection information
        """
        pds_collection_dict = pds_collection.__dict__
        for key in pds_collection_dict.keys():
            value = pds_collection_dict[key]
            # when type is a dictionnary or list, a specific datatype is needed to encode an attribute in HDF5
            if isinstance(value, dict) or isinstance(value, list):
                store_db.attrs[key] = np.string_(str(value))
            elif value is not None:
                store_db.attrs[key] = value

    def _has_changed(
        self, store_db: Any, pds_collection: PdsRegistryModel
    ) -> bool:
        """Check if the same version of the PDS collection has already been stored.

        To check the if the version is an update or not, the comparison is performed based on
        the number of products and the existing keywords `nb_records` in store_db.

        Args:
            store_db (Any): node in HDF5
            pds_collection (PdsRegistryModel): PDS collection

        Returns:
            bool: True when the collection is new or must be updated otherwise False
        """
        return not (
            "nb_records" in store_db
            and pds_collection.NumberProducts == store_db.attrs.nb_records
        )

    def _save_collection(self, pds_collection: PdsRegistryModel, f: Any):
        group_path: str = Database.define_group_from(
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
            store_hdf = f.create_group(group_path)
            self._save_information(store_hdf, pds_collection)
        elif self._has_changed(store_hdf, pds_collection):
            self._save_information(store_hdf, pds_collection)
        else:
            # no update
            pass

    def save_collection(self, pds_collection: PdsRegistryModel):
        """Save the PDS collection in the database.

        Args:
            pds_collection (PdsRegistryModel): the PDS collection
        """
        with h5py.File(self.name, "a") as f:
            self._save_collection(pds_collection, f)

    def save_collections(self, collections_pds: List[PdsRegistryModel]):
        """Save all the PDS collections in the database.

        Args:
            collections_pds (List[PdsRegistryModel]): the collections.
        """
        with h5py.File(self.name, "a") as f:
            for pds_collection in collections_pds:
                self._save_collection(pds_collection, f)

    def _has_attribute_in_group(self, node: Any) -> bool:
        """Check if it exists attributes in the node.

        Args:
            node (Any): the HDF5 node

        Returns:
            bool: True when both the node is a h5py.Group and node has attributes
        """
        return isinstance(node, h5py.Group) and node.attrs

    def _read_and_convert_attributes(self, node: Any) -> Dict[str, Any]:
        """Read and converts convert attributs encoded a nb_bytes_.

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

    def load_collections(self) -> List[PdsRegistryModel]:
        """Load all collections metadata from the database.

        Returns:
            List[PdsRegistryModel]: All PDS collections metadata
        """
        attributes_list: List[PdsRegistryModel] = list()

        def extract_attributes(name: str, node: Any):
            if self._has_attribute_in_group(node):
                dico: Dict[str, Any] = self._read_and_convert_attributes(node)
                attributes_list.append(PdsRegistryModel.from_dict(dico))

        with h5py.File(self.name, "r") as f:
            f.visititems(extract_attributes)

        return attributes_list

    def save_urls(self, pds_collection: PdsRegistryModel, urls: List[str]):
        """Save URLs in the "urls" dataset in a given group where the group name is built from pds_collection

        Args:
            pds_collection (PdsRegistryModel): PDS collection
            urls (List[str]): all pregenerated url to download the data
        """
        with h5py.File(self.name, "a") as f:
            group_path: str = Database.define_group_from(
                [
                    pds_collection.ODEMetaDB.lower(),
                    pds_collection.IHID,
                    pds_collection.IID,
                    pds_collection.PT,
                    pds_collection.DataSetId,
                ]
            )
            old_urls: List[str] = self.load_urls(pds_collection)
            is_same = sorted(urls) == sorted(old_urls)
            if not is_same:
                dset = f.create_dataset(
                    group_path + Database.HDF_SEP + Database.DS_URLS,
                    (len(urls),),
                    dtype=h5py.special_dtype(vlen=str),
                )
                dset[:] = urls
                logger.info(
                    f"Writing {len(urls)} URLs in hdf5:{group_path}/urls"
                )
            else:
                logger.debug(
                    f"These urls {urls} are already stored for {pds_collection}, skip to save the URLs dataset"
                )

    def load_urls(self, pds_collection: PdsRegistryModel) -> List[str]:
        """Loads pregenerated URLs for a given PDS collection.

        Args:
            pds_collection (PdsRegistryModel): PDS collection

        Returns:
            List[str]: List of URLs
        """
        urls: List[str] = list()
        with h5py.File(self.name, "r") as f:
            group_path: str = Database.define_group_from(
                [
                    pds_collection.ODEMetaDB.lower(),
                    pds_collection.IHID,
                    pds_collection.IID,
                    pds_collection.PT,
                    pds_collection.DataSetId,
                ]
            )
            dset = f.get(
                group_path + Database.HDF_SEP + Database.DS_URLS, None
            )
            if dset is not None:
                urls = [item.decode("utf-8") for item in list(dset)]
        return urls

    @staticmethod
    def define_group_from(words: List[str]) -> str:
        """Create a valid name for HDF5 node based on words.

        Args:
            words (List[str]): Words

        Returns:
            str: Valid name for HDF5 node
        """
        return Database.HDF_SEP.join(
            [word.lower().replace("/", "_") for word in words]
        )

    def get_directory_storage_for(
        self, pds_collection: PdsRegistryModel
    ) -> StorageCollectionDirectory:
        return StorageCollectionDirectory(
            self.files_base_directory, pds_collection
        )

    def __repr__(self) -> str:
        return f"Database(base_directory={self.base_directory}, files_base_directory={self.files_base_directory}, stac_directory={self.stac_directory})"
