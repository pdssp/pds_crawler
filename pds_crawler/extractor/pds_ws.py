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
        Provides the list of georeferenced collections.
    PdsRecords :
        Parses the observations metadata as a list of PdsRecordModel model.

Author:
    Jean-Christophe Malapert
"""
import glob
import json
import logging
import os
import urllib.parse
from contextlib import closing
from typing import Any
from typing import Dict
from typing import Generator
from typing import Iterator
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple

from tqdm import tqdm

from ..exception import PdsCollectionAttributeError
from ..load import Database
from ..load import StorageCollectionDirectory
from ..models import PdsRecordsModel
from ..models import PdsRegistryModel
from ..models import VolumeModel
from ..report import MessageModel
from ..utils import compute_download_directory_path
from ..utils import inverse_mapping
from ..utils import Observable
from ..utils import parallel_requests
from ..utils import requests_retry_session
from ..utils import timeit

logger = logging.getLogger(__name__)


class PdsRegistry(Observable):
    """Provides the list of georeferenced collections."""

    SERVICE_ODE_END_POINT = "https://oderest.rsl.wustl.edu/live2/?"

    def __init__(self, database: Database, *args, **kwargs):
        super().__init__()
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.__database = database

    @property
    def database(self) -> Database:
        return self.__database

    def _build_params(self, target: str = None) -> Dict[str, str]:
        params = {"query": "iipy", "output": "json"}
        if target is not None:
            params["odemetadb"] = target
        return params

    def _get_response(self, params) -> str:
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

    def _parse_response_collection(
        self, response: str
    ) -> Tuple[Dict[str, int], List[PdsRegistryModel]]:
        iiptset_dicts = response["ODEResults"]["IIPTSets"]["IIPTSet"]
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
                if pds_collection is not None:
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

    @timeit
    def get_collections_pds(
        self, planet: str = None
    ) -> Tuple[Dict[str, str], List[PdsRegistryModel]]:
        params: Dict[str, str] = self._build_params(planet)
        response: str = self._get_response(params)
        (stats, pds_collection) = self._parse_response_collection(response)
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

    def cache_collections_pds(self, pds_collection: List[PdsRegistryModel]):
        self.database.save_collections(pds_collection)

    def load_pds_collection_from_cache(self) -> List[PdsRegistryModel]:
        return self.database.load_collections()

    def query_cache(self, dataset_id: str) -> List[PdsRegistryModel]:
        pds_collections: List[
            PdsRegistryModel
        ] = self.load_pds_collection_from_cache()
        return [
            pds_collection
            for pds_collection in pds_collections
            if pds_collection.DataSetId == dataset_id
        ]

    def distinct_dataset_values(self) -> Set:
        pds_collections: List[
            PdsRegistryModel
        ] = self.load_pds_collection_from_cache()
        return set(
            [pds_collection.DataSetId for pds_collection in pds_collections]
        )


class PdsRecords(Observable):
    """Parses the observations metadata as a list of PdsRecordModel model."""

    SERVICE_ODE_END_POINT = "https://oderest.rsl.wustl.edu/live2/?"

    def __init__(self, database: Database, *args, **kwargs):
        super().__init__()
        self.__database = database
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)

    @property
    def database(self):
        return self.__database

    def _build_params(
        self,
        target: str,
        ihid: str,
        iid: str,
        pt: str,
        offset: int,
        limit: int = 1000,
    ) -> Dict[str, str]:
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

    def _build_params_for_get_records_pds(
        self,
        target: str,
        ihid: str,
        iid: str,
        pt: str,
        total: int,
        offset: int = 1,
        limit: int = 1000,
    ) -> List[Tuple[str, Any]]:
        params_paginations: List[Tuple[str, Any]] = list()
        pagination_start = offset
        while pagination_start <= total:
            params_paginations.append(
                (target, ihid, iid, pt, total, pagination_start, limit)
            )
            pagination_start = pagination_start + limit
        return params_paginations

    def generate_urls_collection(
        self,
        pds_collection: PdsRegistryModel,
        offset: int = 1,
        limit: int = 5000,
    ):
        params_paginations: List[
            Tuple[str, str]
        ] = self._build_params_for_get_records_pds(
            pds_collection.ODEMetaDB.lower(),
            pds_collection.IHID,
            pds_collection.IID,
            pds_collection.PT,
            pds_collection.NumberProducts,
            offset,
            limit,
        )

        urls: List[str] = list()
        for param in params_paginations:
            param_url = [*param[0:4], *param[5:7]]
            params: Dict[str, str] = self._build_params(*param_url)
            url = PdsRecords.SERVICE_ODE_END_POINT + urllib.parse.urlencode(
                params
            )
            urls.append(url)

        self.database.save_urls(pds_collection, urls)

    def generate_urls_collections(
        self,
        pds_collections: List[PdsRegistryModel],
        offset: int = 1,
        limit: int = 5000,
    ):
        for pds_collection in pds_collections:
            self.generate_urls_collection(pds_collection, offset, limit)

    def download_pds(self, pds_collection: PdsRegistryModel):
        file_storage: StorageCollectionDirectory = (
            self.database.get_directory_storage_for(pds_collection)
        )
        urls: List[str] = self.database.load_urls(pds_collection)
        parallel_requests(file_storage.directory, urls, time_sleep=0.001)

    def download_pds_collections(
        self, pds_collections: List[PdsRegistryModel]
    ):
        for pds_collection in tqdm(
            pds_collections, desc="Getting collections", position=0
        ):
            self.download_pds(pds_collection)

    def parse_pds_collection_from_cache(
        self, pds_collection: PdsRegistryModel, disable_tqdm: bool = False
    ) -> Iterator[PdsRecordsModel]:
        def dsRecordsModelDecoder(dct):
            if "ODEResults" in dct and dct["ODEResults"]["Count"] != "0":
                products_dict = dct["ODEResults"]["Products"]["Product"]
                if not isinstance(products_dict, list):
                    products_dict = [products_dict]
                return PdsRecordsModel.from_dict(products_dict)
            elif "ODEResults" in dct and dct["ODEResults"]["Count"] == "0":
                return None
            return dct

        directory_path: str = compute_download_directory_path(
            self.database.files_base_directory,
            pds_collection.ODEMetaDB,
            pds_collection.IHID,
            pds_collection.IID,
            pds_collection.PT,
            pds_collection.DataSetId,
        )
        # TODO : remove [0:2]
        for file in tqdm(
            glob.glob(f"{directory_path}/*json")[0:2],
            desc="Downloaded responses from the collection",
            disable=disable_tqdm,
            position=1,
            leave=False,
        ):
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
