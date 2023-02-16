# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Module Name:
    pds_ode_website

Description:
    the pds_ode_website module parses the PDS3 Dataset explorer to get the different catalogs.

Classes:
    Crawler :
        Crawles the content of the Dataset explorer web site.
    PDSCatalogDescription :
        Parses the content of the PDS3 catalog.

Author:
    Jean-Christophe Malapert
"""
import logging
import os
import time
from contextlib import closing
from json.decoder import JSONDecodeError
from string import Template
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Union
from urllib.parse import ParseResult
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from bs4 import element
from lark.exceptions import UnexpectedCharacters
from requests.exceptions import ConnectionError
from tqdm import tqdm

from ..exception import NoFileExistInFolder
from ..exception import PdsCatalogDescriptionError
from ..load import Database
from ..load import PdsParserFactory
from ..load import StorageCollectionDirectory
from ..models import CatalogModel
from ..models import PdsRecordModel
from ..models import PdsRecordsModel
from ..models import PdsRegistryModel
from ..models import VolumeModel
from ..report import MessageModel
from ..utils import inverse_mapping
from ..utils import Observable
from ..utils import parallel_requests
from ..utils import requests_retry_session
from .pds_ws import PdsRecords

logger = logging.getLogger(__name__)


class Crawler:
    """Crawles the content of the Dataset explorer web site."""

    def __init__(self, url: str, skip: List[str] = list()):
        super().__init__()
        self.__url: str = url
        url_split: List[str] = url.split("/")
        self._host: str = "/".join(url_split[:-1])
        self._fragment: str = url_split[-1]
        self.__skip: List[str] = skip

    @staticmethod
    def is_file(url: str):
        url_parse: ParseResult = urlparse(url)
        path: str = url_parse.path
        query: str = url_parse.query
        if query:
            return False
        last_fragment = path.split("/")[-1]
        return (
            True
            if "." in last_fragment
            and not last_fragment.split(".")[-1].isnumeric()
            else False
        )

    @staticmethod
    def query(url):
        while True:
            response = None
            try:
                with closing(
                    requests_retry_session().get(
                        url, stream=True, verify=False, timeout=5
                    )
                ) as response:
                    response.encoding = "utf-8"
                    content = response.text
                    return content
            except:  # noqa: E722
                logger.warning(f"Error when trying to query {url}, try again")
                time.sleep(1)
            finally:
                if response is not None:
                    response.close()

    # def _is_intersection(self, list1: List[str], list2: List[str]):
    #     intersection = list(set(list1).intersection(list2))
    #     return len(intersection) > 0

    def _file_ariane(self, soup):
        trs: List[element.Tag] = soup.findAll("tr", bgcolor=True)
        trs_bgcolor = [tr for tr in trs if "#FFFFFF" in tr["bgcolor"]]

        ariane = list()
        for a in trs_bgcolor[0].findAll("a"):
            ariane.append(a.text)

        if len(ariane) == 0:
            ariane.append("Top Level")

        atags: List[element.Tag] = soup.findAll("a", href=True, id=True)
        atags_filtered = [atag for atag in atags if "linksBack" in atag["id"]]
        for sub_volume in atags_filtered:
            ariane.append(sub_volume.text)

        return ariane

    def _get_subdirs_file(self, soup):
        tables: List[element.Tag] = soup.findAll("table")
        links = list()
        for a in tables[-1].findAll("a", href=True, attrs={"title": None}):
            links.append({"url": a["href"], "name": a.text})
        return links

    def _get_content(self, host, query):
        url = host + "/" + query
        if Crawler.is_file(url):
            return None

        content: str = Crawler.query(url)
        if "No files exist in this folder" in content:
            raise NoFileExistInFolder(url)
        soup = BeautifulSoup(content, features="html.parser")
        ariane = self._file_ariane(soup)

        if "/".join(ariane) in self.skip:
            return None

        # logger.info(f"{'...'*len(ariane)}{'/'.join(ariane)} started")
        links = self._get_subdirs_file(soup)
        return links

    def parse(self):
        return self._get_content(self.host, self.fragment)

    @property
    def url(self) -> str:
        return self.__url

    @property
    def host(self) -> str:
        return self._host

    @property
    def fragment(self) -> str:
        return self._fragment

    @property
    def skip(self) -> List[str]:
        return self.__skip


class PDSCatalogDescription(Observable):
    DATASET_EXPLORER = Template(
        "https://ode.rsl.wustl.edu/$ODEMetaDB/DataSetExplorer.aspx?target=$ODEMetaDB&instrumenthost=$ihid&instrumentid=$iid&datasetid=$Data_Set_Id&volumeid=$PDSVolume_Id"
    )

    def __init__(self, database: Database, *args, **kwargs):
        super().__init__()
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.__database: Database = database
        self.__pds_records = PdsRecords(self.__database)
        self._initialize_values()

    def _initialize_values(self):
        self.__pds_collection: PdsRegistryModel = None
        self.__record: PdsRecordModel = None
        self.__url: str = None
        self.__volume_desc_url: str = None
        self.__vol_desc_cat: VolumeModel = None
        self.__catalogs_urls: List[str] = None

    @property
    def url(self) -> str:
        return self.__url

    @property
    def vol_desc_cat(self) -> VolumeModel:
        return self.__vol_desc_cat

    @property
    def volume_desc_url(self) -> str:
        return self.__volume_desc_url

    @property
    def pds_records(self) -> PdsRecords:
        return self.__pds_records

    @property
    def pds_collection(self) -> PdsRegistryModel:
        return self.__pds_collection

    @property
    def database(self) -> Database:
        return self.__database

    @property
    def record(self) -> PdsRecordModel:
        return self.__record

    @property
    def catalogs_urls(self) -> List[str]:
        return self.__catalogs_urls

    def _compute_url(self):
        """Computes the ODE URL.

        This ODE URL is used to parse the web page to get the PDS objects.
        """
        self.__url = PDSCatalogDescription.DATASET_EXPLORER.substitute(
            ODEMetaDB=self.pds_collection.ODEMetaDB.lower(),
            ihid=self.record.ihid,
            iid=self.record.iid,
            Data_Set_Id=self.record.Data_Set_Id,
            PDSVolume_Id=self.record.PDSVolume_Id,
        )

    def _set_volume_desc_url(self):
        """Set the URL volume description by parsing the ODE URL.

        The volume description contains all the references to the interesting catalogs to parse.

        Raises:
            NoFileExistInFolder: voldesc.cat file not found in PDS catalog

        """
        crawler = Crawler(self.url)
        links = crawler.parse()
        vol_desc_url = None
        for link in links:
            if link["name"] == "voldesc.cat":
                vol_desc_url = link["url"]
                break
        if vol_desc_url is None:
            raise NoFileExistInFolder(
                f"voldesc.cat file not found in {self.pds_collection}"
            )
        self.__volume_desc_url: str = vol_desc_url
        logger.info(f"voldesc.cat found in {vol_desc_url}")

    def _parse_vol_desc_cat(self):
        """Set the volume description file by parsing the ODE URL.

        Raises:
            PdsCatalogDescriptionError: Error when getting or parsing the volume description file
        """
        with closing(
            requests_retry_session().get(
                self.volume_desc_url, stream=True, verify=False, timeout=5
            )
        ) as request:
            if request.ok:
                content = request.text
                self.__vol_desc_cat = PdsParserFactory.parse(
                    content, PdsParserFactory.FileGrammary.VOL_DESC
                )
                logger.debug(self.__vol_desc_cat)
            else:
                raise PdsCatalogDescriptionError(
                    f"Error when getting or parsing {self.volume_desc_url}"
                )

    def _retrieve_vol_desc_cat(self):
        """Retrieves the volume description file, parses it and store it as attribute

        Raises:
            NoFileExistInFolder: voldesc.cat file not found in PDS catalog
            PdsCatalogDescriptionError: Error when getting or parsing the volume description file
        """
        self._set_volume_desc_url()
        self._parse_vol_desc_cat()

    def _retrieve_catalogs_path(self) -> List[Dict[str, str]]:
        """Retrieve the URL of the PDS object by parsing the ODE URL.

        Returns:
            List[Dict[str, str]]: Catalogs name and its URL
        """
        url = self.url + "&pathtovol=catalog/"
        result: List[Dict[str, str]]
        try:
            crawler = Crawler(url)
            result = crawler.parse()
        except NoFileExistInFolder as err:
            self.notify_observers(MessageModel(url, err))
            logger.error(f"[NoFileExistInFolder]: {url}")
            result = list()
        return result

    def _is_catalog_exists(self, catalog_name: Any) -> bool:
        """Checks if the catalog_name is set.

        Args:
            catalog_name (Any): object to test

        Returns:
            bool: True if the cataloh_name is not None otherwise False
        """
        return catalog_name is not None

    def _get_url_for_multiple_catalogs(
        self, catalogs: List[str], catalogs_from_desc_cat: Dict[str, str]
    ) -> List[str]:
        """Get the URLs for all the PDS objects

        Args:
            catalogs (List[str]): PDS object name
            catalogs_from_desc_cat (Dict[str, str]): _description_

        Returns:
            List[str]: Returns the URLs of the PDS objects
        """
        url_list: List[str] = list()
        for catalog_name in catalogs:
            catalog_name_lower: str = catalog_name.lower()
            if catalog_name_lower in catalogs_from_desc_cat:
                url: str = catalogs_from_desc_cat[catalog_name_lower]
                url_list.append(url)
            else:
                logger.error(f"Cannot find {catalog_name_lower} catalog")
        return url_list

    def _get_url_for_simple_catalog(
        self, catalog_name: str, catalogs_from_desc_cat: Dict[str, str]
    ) -> List[str]:
        url_list: List[str] = list()
        catalog_name_lower: str = catalog_name.lower()
        if catalog_name_lower in catalogs_from_desc_cat:
            url: str = catalogs_from_desc_cat[catalog_name_lower]
            url_list.append(url)
        else:
            logger.error(f"Cannot find {catalog_name_lower} catalog")
        return url_list

    def _get_urls_from_catalog(
        self,
        catalog_name: Union[str, List[str]],
        catalogs_from_desc_cat: Dict[str, str],
    ) -> List[str]:
        url_list: List[str] = list()
        if self._is_catalog_exists(catalog_name):
            if isinstance(catalog_name, list):
                url_list.extend(
                    self._get_url_for_multiple_catalogs(
                        catalog_name, catalogs_from_desc_cat
                    )
                )
            else:
                url_list.extend(
                    self._get_url_for_simple_catalog(
                        catalog_name, catalogs_from_desc_cat
                    )
                )
        return url_list

    def _retrieve_catalogs_urls(self) -> List[str]:
        self._compute_url()
        self._retrieve_vol_desc_cat()
        catalog_paths: List[Dict[str, str]] = self._retrieve_catalogs_path()
        mapping_file_url: Dict[str, str] = {
            catalog["name"]: catalog["url"] for catalog in catalog_paths
        }
        url_list: List[str] = list()
        catalog: CatalogModel = self.vol_desc_cat.CATALOG
        catalog_dict: Dict[str, str] = catalog.__dict__
        for key in catalog_dict.keys():
            url_list.extend(
                self._get_urls_from_catalog(
                    catalog_dict[key], mapping_file_url
                )
            )
        return url_list

    def retrieve_catalogs(self, pds_collection: PdsRegistryModel):
        """Retrieves the catalogs URLs for a given `pds_collection` collection

        Args:
            pds_collection (PdsRegistryModel): PDS collection
        """
        self._initialize_values()
        self.__pds_collection = pds_collection
        records_iter: Iterator[
            PdsRecordsModel
        ] = self.pds_records.parse_pds_collection_from_cache(
            pds_collection,
            disable_tqdm=True,
        )
        try:
            records: PdsRecordsModel = next(records_iter)
            self.__record = records.pds_records_model[0]
            try:
                self.__catalogs_urls: List[
                    str
                ] = self._retrieve_catalogs_urls()
            except NoFileExistInFolder as err:
                logger.exception(f"[NoFileExistInFolder]: {err}")
                self.notify_observers(MessageModel(pds_collection, err))
            except UnexpectedCharacters as err:
                logger.exception(f"[ParserError]: {err}")
                self.notify_observers(MessageModel(pds_collection, err))
            except ConnectionError as err:
                logger.exception(f"[ConnectionError]: {err}")
                self.notify_observers(MessageModel(pds_collection, err))
        except StopIteration:
            logger.error(f"No record for {pds_collection}")
            self.notify_observers(
                MessageModel(pds_collection, Exception("No record"))
            )
        except JSONDecodeError:
            logger.error(
                f"[CorruptedFile] Please remove the file corresponding to this collection {pds_collection}"
            )
            self.notify_observers(
                MessageModel(
                    pds_collection,
                    Exception("[CorruptedFile] Please remove the file"),
                )
            )

    def _parse_catalog(
        self,
        file_storage: StorageCollectionDirectory,
        catalog_name: str,
        cat_type: str,
        result: Dict[str, Union[str, List[str]]],
    ):
        """Parses the PDS object

        Args:
            file_storage (StorageCollectionDirectory): storage where the PDS objects have been downloaded
            catalog_name (str): catalog name
            cat_type (str): Object to load to parse the catalog
            result (Dict[str, Union[str, List[str]]]): the catalogs in the Volume description
        """
        try:
            cat_obj = file_storage.get_catalog(
                catalog_name,
                PdsParserFactory.FileGrammary.get_enum_from(cat_type),
            )
            if cat_type in result:
                result[cat_type].append(cat_obj)
            else:
                result[cat_type] = cat_obj
        except KeyError as err:
            message = (
                f"Unable to find {catalog_name} in {file_storage.directory}"
            )
            logger.error(message)
            logger.exception(err)
            self.notify_observers(
                MessageModel(catalog_name, Exception(message))
            )
        except UnicodeDecodeError as err:
            message = (
                f"Unable to find {catalog_name} in {file_storage.directory}"
            )
            logger.error(message)
            logger.exception(err)
            self.notify_observers(
                MessageModel(catalog_name, Exception(message))
            )
        except Exception as err:
            message = (
                f"Unable to parse {catalog_name} in {file_storage.directory}"
            )
            logger.error(message)
            logger.exception(err)
            self.notify_observers(
                MessageModel(catalog_name, Exception(message))
            )

    def get_ode_catalogs(
        self, pds_collection: PdsRegistryModel
    ) -> Dict[str, Any]:
        """Returns the PDS object for a given space mission collection.

        Args:
            pds_collection (PdsRegistryModel): the space mission collection

        Raises:
            TypeError: Illegal datatype for catalog

        Returns:
            Dict[str, Any]: list of PDS Object name and its object
        """
        result = dict()
        result["collection"] = pds_collection
        try:
            file_storage: StorageCollectionDirectory = (
                self.database.get_directory_storage_for(pds_collection)
            )
            result["volume"] = file_storage.get_volume_description()
            catalogs: Dict[
                str, Union[str, List[str]]
            ] = file_storage.list_catalogs()
            for cat_type in catalogs.keys():
                catalog_s: Union[str, List[str]] = catalogs[cat_type]
                if catalog_s is None:
                    continue
                elif isinstance(catalog_s, str):
                    self._parse_catalog(
                        file_storage, catalog_s, cat_type, result
                    )
                elif isinstance(catalog_s, list):
                    result[cat_type] = list()
                    for catalog_name in catalog_s:
                        self._parse_catalog(
                            file_storage, catalog_name, cat_type, result
                        )
                else:
                    raise TypeError(
                        f"Illegal datatype for catalog : {type(catalog_s)}"
                    )

            return result
        except FileNotFoundError as err:
            logger.exception(err)
            return result

    def __repr__(self) -> str:
        return f"PDSCatalogDescription({self.pds_records})"


class PDSCatalogsDescription(Observable):
    """Provides the means to download the PDS catalogs (PDS objects)."""

    def __init__(self, database: Database, *args, **kwargs):
        super().__init__()
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.__pds_catalogs = PDSCatalogDescription(database, *args, **kwargs)
        self.__database = database

    @property
    def pds_catalogs(self) -> PDSCatalogDescription:
        return self.__pds_catalogs

    @property
    def database(self) -> Database:
        return self.__database

    def _build_all_urls(self, pds_collection: PdsRegistryModel) -> List[str]:
        """Builds all the PDS objects URLs for collections of space missions.

        These URLs are used to retrieve all PDS objects.

        Args:
            pds_collection (PdsRegistryModel): the collections of space missions

        Returns:
            List[str]: List of URLs
        """
        urls_list: List[str] = list()
        self.pds_catalogs.retrieve_catalogs(pds_collection)
        urls: List[str] = self.pds_catalogs.catalogs_urls
        if urls is not None:
            urls_list.extend(urls)
            urls_list.append(self.pds_catalogs.volume_desc_url)
        return urls_list

    def download(self, pds_collections: List[PdsRegistryModel]):
        """Downloads the PDS objects for the collections of space missions.

        Args:
            pds_collections (List[PdsRegistryModel]): the collections of space missions
        """
        for pds_collection in pds_collections:
            urls_list: List[str] = self._build_all_urls(pds_collection)
            try:
                file_storage: StorageCollectionDirectory = (
                    self.database.get_directory_storage_for(pds_collection)
                )
                parallel_requests(file_storage.directory, urls_list, timeout=5)
            except UnexpectedCharacters as err:
                logger.exception(f"[ParserError]: {err}")
            except ConnectionError as err:
                logger.exception(f"[ConnectionError]: {err}")

    def get_ode_catalogs(
        self, pds_collections: List[PdsRegistryModel]
    ) -> Iterator[Dict[str, Any]]:
        """Get all the PDS objects for the `pds_collections`.

        Args:
            pds_collections (List[PdsRegistryModel]): the collections of the space mission.

        Yields:
            Iterator[Dict[str, Any]]: PDS object name and its object
        """
        for pds_collection in pds_collections:
            yield self.pds_catalogs.get_ode_catalogs(pds_collection)
