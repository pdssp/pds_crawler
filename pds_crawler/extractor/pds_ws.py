# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Module Name:
    pds_ws

Description:
    the pds_ws provides the metadata for the observations by querying ODE web services.

Classes:
    PdsRegistry :
        Provides the list of georeferenced PDS collections by retrieving
        a list of Planetary Data System (PDS) data collections rom the
        PDS ODE (Outer Planets Data Exploration) web service.
    PdsRecords :
        Handles the PDS records (download, store and load the records for
        one of several PDS collection).

Author:
    Jean-Christophe Malapert
"""
import json
import logging
import os
import urllib.parse
from contextlib import closing
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from tqdm import tqdm

from ..exception import PdsCollectionAttributeError
from ..load import Database
from ..load import PdsCollectionStorage
from ..models import PdsRecordsModel
from ..models import PdsRegistryModel
from ..report import MessageModel
from ..utils import Observable
from ..utils import requests_retry_session

logger = logging.getLogger(__name__)


class PdsRegistry(Observable):
    """Provides the list of georeferenced PDS collections by retrieving
    a list of Planetary Data System (PDS) data collections rom the
    PDS ODE (Outer Planets Data Exploration) web service.

    .. mermaid::

        classDiagram
            class PdsRegistry {
                +Database database
                - build_params(target: str = None) Dict[str, str]
                - get_response(params: Dict[str, str]) str
                - parse_response_collection(response: str) Tuple[Dict[str, int], List[PdsRegistryModel]]
                + get_pds_collections(planet: str = None) Tuple[Dict[str, str], List[PdsRegistryModel]]
                + cache_pds_collections(pds_collections: List[PdsRegistryModel])
                + load_pds_collections_from_cache() List[PdsRegistryModel]
                + query_cache(dataset_id: str) Optional[PdsRegistryModel]
                + distinct_dataset_values() Set
            }
    """

    SERVICE_ODE_END_POINT = "https://oderest.rsl.wustl.edu/live2/?"

    def __init__(self, database: Database, *args, **kwargs):
        """Initializes the collection by setting a database to store the content that has
        been retrieved from the PDS

        Args:
            database (Database): database
        """
        super().__init__()
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.__database = database

    @property
    def database(self) -> Database:
        """Returns the database

        Returns:
            Database: database
        """
        return self.__database

    def _build_request_params(
        self, target: Optional[str] = None
    ) -> Dict[str, str]:
        """Build the query parameters.

        Args:
            target (str, optional): target. Defaults to None.

        Returns:
            Dict[str, str]: Query parameters
        """
        params = {"query": "iipy", "output": "json"}
        if target is not None:
            params["odemetadb"] = target
        return params

    def _get_response(self, params: Dict[str, str]) -> str:
        """Returns the content of web service response designed by
        the SERVICE_ODE_END_POINT and the query params.

        Args:
            params (Dict[str, str]): Query parameters

        Raises:
            Exception: PDS ODE REST API query error

        Returns:
            str: the content of the web service response
        """
        content: str
        with closing(
            requests_retry_session().get(
                PdsRegistry.SERVICE_ODE_END_POINT,
                params=params,
                timeout=(180, 1800),
            )
        ) as response:
            url: str = response.url
            logger.debug(
                f"Requesting {url} to get the collections: \
                    {params['odemetadb'] if 'odemetadb' in params else 'All'}"
            )
            if response.ok:
                content = response.json()
            else:
                raise Exception(
                    f"PDS ODE REST API query {response.status_code} \
                    error: url={url}"
                )
        return content

    def _parse_collection_response(
        self, response: str, dataset_id: Optional[str] = None
    ) -> Tuple[Dict[str, int], List[PdsRegistryModel]]:
        """Parses the JSON response and returns a tuple that contains a
        statistic dictionary and a list of PdsRegistryModel objects.

        Args:
            response (str): JSON response
            dataset_id (Optional[str]): dataset_id parameter, used to filter the response. Defaults to None

        Returns:
            Tuple[Dict[str, int], List[PdsRegistryModel]]: statistic dictionary and a list of PdsRegistryModel objects
        """
        iiptset_dicts = response["ODEResults"]["IIPTSets"]["IIPTSet"]  # type: ignore
        nb_records: int = 0
        total: int = len(iiptset_dicts)
        errors: int = 0
        skip: int = 0
        nb_collections: int = 0
        pds_collections: List[PdsRegistryModel] = list()
        for iiptset_dict in iiptset_dicts:
            try:
                pds_collection: PdsRegistryModel = PdsRegistryModel.from_dict(
                    iiptset_dict
                )
                if pds_collection is not None and (
                    dataset_id is None
                    or pds_collection.DataSetId.upper() == dataset_id.upper()
                ):
                    nb_records += pds_collection.NumberProducts
                    pds_collections.append(pds_collection)
            except PdsCollectionAttributeError as err:
                errors += 1
                logger.error(err)
        nb_collections: int = len(pds_collections)
        skip = total - (nb_collections + errors)
        stats = {
            "skip": skip,
            "errors": errors,
            "count": len(iiptset_dicts),
            "nb_records": nb_records,
        }
        return (stats, pds_collections)

    def get_pds_collections(
        self, planet: Optional[str] = None, dataset_id: Optional[str] = None
    ) -> Tuple[Dict[str, int], List[PdsRegistryModel]]:
        """Retrieve a list of Planetary Data System (PDS) data collections
        from the PDS ODE (Outer Planets Data Exploration) web service.

        The method takes an optional planet argument that specifies the name
        of the planet for which to retrieve collections. If no argument is
        provided, the method retrieves collections for all planets.
        The method sends an HTTP request to the PDS ODE web service with the
        appropriate parameters constructed from the planet argument and
        parses the JSON response to extract the data collections.
        It then returns a tuple containing a dictionary of statistics and
        a list of PdsRegistryModel objects representing the data collections.

        Args:
            planet (str, optional): planet. Defaults to None.
            dataset_id (str, optional): dataset ID. Defaults to None.

        Returns:
            Tuple[Dict[str, str], List[PdsRegistryModel]]: a dictionary of s
            tatistics and a list of PdsRegistryModel objects representing the
            data collections
        """
        request_params: Dict[str, str] = self._build_request_params(planet)
        response: str = self._get_response(request_params)
        (stats, pds_collection) = self._parse_collection_response(
            response, dataset_id
        )
        logger.info(
            f"""
        ODE Summary
        -----------
        Nb records = {stats['nb_records']}
        Nb collections : {len(pds_collection)}/{stats['count']}
        Nb errors : {stats['errors']}
        Nb skip : {stats['skip']}"""
        )
        return (stats, pds_collection)

    def cache_pds_collections(self, pds_collections: List[PdsRegistryModel]):
        """Caches the PDS collections information by saving the PDS
        collections in the database.

        Args:
            pds_collections (List[PdsRegistryModel]): the PDS collections information
        """
        self.database.hdf5_storage.save_collections(pds_collections)

    def load_pds_collections_from_cache(
        self, planet: Optional[str] = None, dataset_id: Optional[str] = None
    ) -> List[PdsRegistryModel]:
        """Loads the PDS collections information from the cache by loading
        the information from the database.

        Args:
            planet (Optional[str], optional): name of the planet to get. Defaults to None.
            dataset_id (Optional[str], optional): Dataset ID parameter, used to filter the collection. Defaults to None.

        Returns:
            List[PdsRegistryModel]: the PDS collections information
        """
        return self.database.hdf5_storage.load_collections(planet, dataset_id)

    def query_cache(self, dataset_id: str) -> Optional[PdsRegistryModel]:
        """Query a local cache of PDS data collections for a specific
        dataset identified by its ID.

        Args:
            dataset_id (str): ID of thr dataset

        Returns:
            Optional[PdsRegistryModel]: PDS data collection
        """
        result: Optional[PdsRegistryModel] = None
        for collection in self.load_pds_collections_from_cache():
            if collection.DataSetId == dataset_id:
                result = collection
                break
        return result

    def distinct_dataset_values(self) -> Set:
        """Gets a set of distinct values for the DataSetId attribute of
        PdsRegistryModel objects in a local cache of PDS data collections.

        Returns:
            Set: Distinct values for the DataSetId attribute
        """
        pds_collections: List[
            PdsRegistryModel
        ] = self.load_pds_collections_from_cache()
        return set(
            [pds_collection.DataSetId for pds_collection in pds_collections]
        )


class PdsRecords(Observable):
    """Handles the PDS records.

    Responsible to download and stores the JSON response in the database. This class is also
    responsible to parse the stored JSON and converts each record in the PdsRecordsModel.

    .. mermaid::

        classDiagram
            class PdsRecords {
                +Database database
                - build_params(target: str, ihid: str, iid: str, pt: str, offset: int, limit: int = 1000,) Dict[str, str]
                - generate_all_pagination_params(target: str, ihid: str, iid: str, pt: str, total: int, offset: int = 1, limit: int = 1000) List[Tuple[str, Any]]
                - __repr__(self) str
                + generate_urls_for_one_collection(pds_collection: PdsRegistryModel, offset: int = 1, limit: int = 5000):
                + generate_urls_for_all_collections(pds_collection: List[PdsRegistryModel], offset: int = 1, limit: int = 5000)
                + generate_urls_for_all_collections(pds_collections: List[PdsRegistryModel], offset: int = 1, limit: int = 5000)
                + download_pds_records_for_one_collection(pds_collection: PdsRegistryModel, limit: Optional[int] = None)
                + download_pds_records_for_all_collections(pds_collections: List[PdsRegistryModel])
                + parse_pds_collection_from_cache(pds_collection: PdsRegistryModel, disable_tqdm: bool = False) Iterator[PdsRecordsModel]
            }
    """

    SERVICE_ODE_END_POINT = "https://oderest.rsl.wustl.edu/live2/?"

    def __init__(self, database: Database, *args, **kwargs):
        super().__init__()
        self.__database = database
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.__nb_workers: int = 3

    @property
    def database(self) -> Database:
        """Returns the database

        Returns:
            Database: database
        """
        return self.__database

    @property
    def nb_workers(self) -> int:
        """Returns the number of workers

        Returns:
            int: number of workers
        """
        return self.__nb_workers

    @nb_workers.setter
    def nb_workers(self, value: int):
        self.__nb_workers = value

    def _build_request_params(
        self,
        target: str,
        ihid: str,
        iid: str,
        pt: str,
        offset: int,
        limit: int = 1000,
    ) -> Dict[str, str]:
        """Builds the query parameters.

        Args:
            target (str): planet
            ihid (str): plateforme
            iid (str): instrument
            pt (str): product type
            offset (int): record number where the pagination start
            limit (int, optional): number of records in the response. Defaults to 1000.

        Returns:
            Dict[str, str]: key/value to prepare the query
        """
        params = {
            "query": "product",
            "target": target,
            "results": "copmf",
            "ihid": ihid,
            "iid": iid,
            "pt": pt,
            "offset": offset,
            "limit": limit,
            "output": "json",
        }
        return params

    def _generate_all_pagination_params(
        self,
        target: str,
        ihid: str,
        iid: str,
        pt: str,
        total: int,
        offset: int = 1,
        limit: int = 1000,
    ) -> List[Tuple[str, Any]]:
        """Generates all pagination parameters

        Args:
            target (str): planet
            ihid (str): plateform
            iid (str): instrument
            pt (str): product type
            total (int): total number of records that we want
            offset (int, optional): record number where the pagination starts. Defaults to 1.
            limit (int, optional): maximum number of records in the response. Defaults to 1000.

        Returns:
            List[Tuple[str]]: List of (target, ihid, iid, pt, total, pagination_start, limit)
        """
        params_paginations: List[Tuple[str, Any]] = list()
        pagination_start = offset
        while pagination_start <= total:
            params_paginations.append(
                (target, ihid, iid, pt, total, pagination_start, limit)  # type: ignore
            )
            pagination_start = pagination_start + limit
        return params_paginations

    def generate_urls_for_one_collection(
        self,
        pds_collection: PdsRegistryModel,
        offset: int = 1,
        limit: int = 5000,
    ):
        """Generates the URLs for one collection and save them in the database.

        There Urls will be used to dowload massively the records.

        Args:
            pds_collection (PdsRegistryModel): pds collection
            offset (int, optional): record number from which the response starts. Defaults to 1.
            limit (int, optional): maximum number of records per page. Defaults to 5000.
        """
        all_pagination_params: List[
            Tuple[str]
        ] = self._generate_all_pagination_params(
            pds_collection.ODEMetaDB.lower(),  # type: ignore
            pds_collection.IHID,
            pds_collection.IID,
            pds_collection.PT,
            pds_collection.NumberProducts,
            offset,
            limit,
        )

        urls: List[str] = list()
        for pagination_params in all_pagination_params:
            param_url = [*pagination_params[0:4], *pagination_params[5:7]]
            request_params: Dict[str, str] = self._build_request_params(
                *param_url  # type: ignore
            )
            url = PdsRecords.SERVICE_ODE_END_POINT + urllib.parse.urlencode(
                request_params
            )
            urls.append(url)

        self.database.hdf5_storage.save_urls(pds_collection, urls)

    def generate_urls_for_all_collections(
        self,
        pds_collections: List[PdsRegistryModel],
        offset: int = 1,
        limit: int = 5000,
    ):
        """Generates the URLs for all the collections and save them in the database.

        There Urls will be used to dowload massively the records.

        Args:
            pds_collections (List[PdsRegistryModel]): PDS collections
            offset (int, optional): record number. Defaults to 1.
            limit (int, optional): limit per page. Defaults to 5000.
        """
        for pds_collection in pds_collections:
            self.generate_urls_for_one_collection(
                pds_collection, offset, limit
            )

    def download_pds_records_for_one_collection(
        self, pds_collection: PdsRegistryModel, limit: Optional[int] = None
    ):
        """Download records for a given PDS collection based on the set of
        URLs loaded from the database.

        Args:
            pds_collection (PdsRegistryModel): PDS collection
            limit (Optional[int], optional): _description_. Defaults to None.
        """
        urls: List[str] = self.database.hdf5_storage.load_urls(pds_collection)
        if len(urls) == 0:
            self.generate_urls_for_one_collection(pds_collection)
            urls = self.database.hdf5_storage.load_urls(pds_collection)
        if limit is not None:
            urls = urls[0:limit]

        file_storage: PdsCollectionStorage = (
            self.database.pds_storage.get_pds_storage_for(pds_collection)
        )
        file_storage.download(urls, time_sleep=1, nb_workers=self.nb_workers)

    def download_pds_records_for_all_collections(
        self,
        pds_collections: List[PdsRegistryModel],
        limit: Optional[int] = None,
    ):
        """Download PDS records for all collections

        Args:
            pds_collections (List[PdsRegistryModel]): _description_
            limit (Optional[int], optional): _description_. Defaults to None.
        """
        for pds_collection in tqdm(
            pds_collections, desc="Getting collections", position=0
        ):
            self.download_pds_records_for_one_collection(pds_collection, limit)

    def parse_pds_collection_from_cache(
        self, pds_collection: PdsRegistryModel, disable_tqdm: bool = False
    ) -> Iterator[PdsRecordsModel]:
        """Parses the PDS records from cache.

        Responsible for parsing PDS records from the local cache of the PDS catalogs.

        It takes a PdsRegistryModel object as input, which contains the metadata needed
        to locate the downloaded PDS records in the local cache.

        If the parsing is successful and the resulting PdsRecordsModel object is not None,
        the method yields the object. If the parsing fails, the method logs an error message
        and notifies its observers with a MessageModel object containing information about
        the file and the error.

        Args:
            pds_collection (PdsRegistryModel): PDS collection of the registry
            disable_tqdm (bool, optional): use tqdm. Defaults to False.

        Yields:
            Iterator[PdsRecordsModel]: Iterator on the list of records_
        """

        def dsRecordsModelDecoder(dct):
            if "ODEResults" in dct and dct["ODEResults"]["Count"] != "0":
                products_dict = dct["ODEResults"]["Products"]["Product"]
                if not isinstance(products_dict, list):
                    products_dict = [products_dict]
                return PdsRecordsModel.from_dict(products_dict)
            elif "ODEResults" in dct and dct["ODEResults"]["Count"] == "0":
                return None
            return dct

        # TODO : remove glob.glob(f"{directory_path}/*json")[0:2]
        collection_storage: PdsCollectionStorage = (
            self.database.pds_storage.get_pds_storage_for(pds_collection)
        )
        for file in tqdm(
            collection_storage.list_files(),
            desc="Downloaded responses from the collection",
            disable=disable_tqdm,
            position=1,
            leave=False,
        ):
            file = os.path.join(collection_storage.directory, file)
            content: str
            with open(file, encoding="utf8", errors="ignore") as f:
                content = f.read()
                try:
                    result = json.loads(
                        content, object_hook=dsRecordsModelDecoder
                    )
                    if result is not None:
                        yield result
                except json.JSONDecodeError as err:
                    message = f"{file} must be deleted !"
                    logger.error(message)
                    self.notify_observers(MessageModel(file, err))

    def __repr__(self) -> str:
        return f"PdsRecords({self.database})"
