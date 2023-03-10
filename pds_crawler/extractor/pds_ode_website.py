# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Module Name:
    pds_ode_website

Description:
    the pds_ode_website module parses the PDS3 Dataset explorer to get the different catalogs
    to download them.

Classes:
    Crawler :
        Crawles the content of the Dataset explorer web site.
    PDSCatalogDescription :
        Parses the content of the PDS3 catalogs for a given PDS collection.
    PDSCatalogsDescription :
        Downloads the PDS3 objects (catalogs) on the local storage and parses the
        PDS3 objects from the local storage

Author:
    Jean-Christophe Malapert
"""
import logging
import time
from contextlib import closing
from json.decoder import JSONDecodeError
from string import Template
from typing import Any
from typing import cast
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Union
from urllib.parse import parse_qs
from urllib.parse import ParseResult
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from bs4 import element
from lark.exceptions import UnexpectedCharacters
from requests.exceptions import ConnectionError

from ..exception import NoFileExistInFolder
from ..exception import PdsCatalogDescriptionError
from ..load import Database
from ..load import PdsCollectionStorage
from ..load import PdsParserFactory
from ..models import CatalogModel
from ..models import PdsRecordModel
from ..models import PdsRecordsModel
from ..models import PdsRegistryModel
from ..models import VolumeModel
from ..report import MessageModel
from ..utils import Observable
from ..utils import parallel_requests
from ..utils import requests_retry_session
from .pds_ode_ws import PdsRecordsWs

logger = logging.getLogger(__name__)


class Crawler:
    """Crawles the content of the Dataset explorer web site.

    The main purpose of the class is to retrieve the links and subdirectories
    from the given web page and return them as a list. The class also checks
    if a given URL is a file or a directory and raises an exception if no files
    exist in the folder.

    .. uml::

        class Crawler {
            + str url
            + str host
            + str fragment
            - get_subdirs_file(soup) List[Dict[str, str]]
            - get_content(host: str, query: str) Optional[List[Dict[str, str]]]
            + static is_file(url: str) bool
            + static query(url: str) str
            + parse() -> Optional[List[Dict[str, str]]]
        }
    """

    def __init__(self, url: str):
        """Initializes the Crawler with an URL

        Args:
            url (str): URL
        """
        super().__init__()
        self.__url: str = url
        url_split: List[str] = url.split("/")
        self._host: str = "/".join(url_split[:-1])
        self._fragment: str = url_split[-1]

    @staticmethod
    def is_file(url: str) -> bool:
        """Tests whether the URL points to a file or not.

        The method extracts the last fragment of the path,
        which is usually the name of the file or directory
        being pointed to. If the last fragment contains a
        period (".") character, it is considered to be a
        file and not a directory. The method then checks
        if the characters after the last period character
        are numeric (indicating a file with an extension
        like ".mp3" or ".txt"), and if they are not numeric,
        it returns True to indicate that the URL points to a file.

        Args:
            url (str): URL

        Returns:
            bool: True if the URL points to a File otherwise False
        """
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
    def query(url: str) -> str:
        """Extracts the content of the URL with 3 retries with a timeout of 5s

        Args:
            url (str): URL

        Returns:
            str: the content of the URL
        """
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

    def _get_subdirs_file(self, soup) -> List[Dict[str, str]]:
        """Parses the HTML content of a web page, and extracts
        links to subdirectories and files from the page.

        The method first finds all "table" elements in the parsed HTML content
        and stores them in a list. It then creates an empty list called "links"
        to store the links that it finds.

        Next, the method looks for "a" elements within the last table in the
        list of tables. It only considers "a" elements that have an "href"
        attribute and do not have a "title" attribute. For each "a" element
        that meets these criteria, the method creates a dictionary with two
        key-value pairs: "url" and "name". The "url" value is set to the value
        of the "href" attribute, which is the URL of the link. The "name" value
        is set to the text content of the "a" element, which is usually the
        name of the subdirectory or file.

        Args:
            soup (_type_): Soup

        Returns:
            List[Dict[str, str]]: links
        """
        tables: List[element.Tag] = soup.findAll("table")
        links = list()
        for a in tables[-1].findAll("a", href=True, attrs={"title": None}):
            links.append({"url": a["href"], "name": a.text})
        return links

    def _get_content(self, host: str, query: str) -> List[Dict[str, str]]:
        """Get the content of an URL based on the host and the query

        Args:
            host (str): host
            query (str): query

        Raises:
            NoFileExistInFolder: When there is no file in the folder

        Returns:
            List[Dict[str, str]]: links (url/name)
        """
        url = host + "/" + query
        if Crawler.is_file(url):
            raise ValueError(f"URL {url} is a file")

        content: str = Crawler.query(url)
        if "No files exist in this folder" in content:
            raise NoFileExistInFolder(url)
        soup = BeautifulSoup(content, features="html.parser")
        links = self._get_subdirs_file(soup)
        return links

    def parse(self) -> List[Dict[str, str]]:
        """Parse the URL

        Returns:
            List[Dict[str, str]]: links (url/name)
        """
        return self._get_content(self.host, self.fragment)

    @property
    def url(self) -> str:
        """Returns the URL to parse

        Returns:
            str: URL
        """
        return self.__url

    @property
    def host(self) -> str:
        """Returns the host of the query

        Returns:
            str: host
        """
        return self._host

    @property
    def fragment(self) -> str:
        """Returns the fagment of the URL

        Returns:
            str: the fagment of the URL
        """
        return self._fragment


class PDSCatalogDescription(Observable):
    """Class that handles the PDS catalogs, based on the PDS3 objects.

    This class can :

    * load the URLs of all PDS catalogs for a given collection from the ODE web site.
    * get ODE catalogs objects from local storage

    Note : The download of the PDS catalogs in the local storage is done
    by the PDSCatalogsDescription object, which performs a massive download
    in the local storage

    .. uml::

        class PDSCatalogDescription {
            - Any report
            + str url
            + VolumeModel vol_desc_cat
            + str volume_desc_url
            + PdsRecordsWs pds_records
            + PdsRegistryModel pds_collection
            + database Database
            + PdsRecordsModel record
            + List[str] catalogs_urls
            - build_url_ode_collection()
            - find_volume_desc_url() str
            - parse_volume_desc_cat() VolumeModel
            - load_volume_description()
            - find_catalogs_urls() -> List[Dict[str, str]]
            - is_catalog_exists(catalog_name: Any) -> bool
            - get_url_for_multiple_catalogs(catalogs: List[str], catalogs_from_desc_cat: Dict[str, str]) List[str]
            - get_url_for_simple_catalog(catalog_name: str, catalogs_from_desc_cat: Dict[str, str]) List[str]
            - get_urls_from_catalog_type(catalog_name: Union[str, List[str]], catalogs_from_desc_cat: Dict[str, str]) List[str]
            - parse_catalog(file_storage: PdsStorage, catalog_name: str, cat_type: str, result: Dict[str, Union[str, List[str]]])
            + load_catalogs_urls() List[str]
            + get_ode_catalogs(pds_collection: PdsRegistryModel)  Dict[str, Any]
            + __repr__(self) str
        }
    """

    DATASET_EXPLORER = Template(
        "https://ode.rsl.wustl.edu/$ODEMetaDB/DataSetExplorer.aspx?target=$ODEMetaDB&instrumenthost=$ihid&instrumentid=$iid&datasetid=$Data_Set_Id"
    )

    def __init__(self, database: Database, *args, **kwargs):
        """Initialize the object with a database to store the information.

        Args:
            database (Database): database
        """
        super().__init__()
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.__database: Database = database
        self.__pds_records = PdsRecordsWs(self.__database)
        self._initialize_values()

    def _initialize_values(self):
        """Initialize the values"""
        self.__pds_collection: PdsRegistryModel
        self.__record: PdsRecordModel
        self.__url: str
        self.__volume_desc_url: str
        self.__vol_desc_cat: VolumeModel
        self.__catalogs_urls: List[str] = list()

    @property
    def url(self) -> str:
        """ODE URL that hosts the PDS catalogs

        Returns:
            str: URL
        """
        return self.__url

    @property
    def vol_desc_cat(self) -> VolumeModel:
        """Returns the volume description catalog.

        Returns:
            VolumeModel: the volume description catalog
        """
        return self.__vol_desc_cat

    @property
    def volume_desc_url(self) -> str:
        """The volume description URL

        Returns:
            str: the volume description URL
        """
        return self.__volume_desc_url

    @property
    def pds_records(self) -> PdsRecordsWs:
        """Returns the PDS records object to access to the data from the local cache.

        Returns:
            PdsRecordsWs: PDS records
        """
        return self.__pds_records

    @property
    def pds_collection(self) -> PdsRegistryModel:
        """PDS collection that contains the PDS catalogs.

        Returns:
            PdsRegistryModel: _description_
        """
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

    def _build_url_ode_collection(self, volume_id: Optional[str] = None):
        """Computes the ODE URL.

        This ODE URL is used to parse the web page to get the PDS objects.
        Sometimes the volume_id value is renamed. In this case, the web page
        must be parsed by getting the volume_id label to find the correct volume_id

        Args:
            with_volume_id (str, optional): volume_id to set. Defaults to None.
        """
        url_build: str = PDSCatalogDescription.DATASET_EXPLORER.substitute(
            ODEMetaDB=self.pds_collection.ODEMetaDB.lower(),
            ihid=self.record.ihid,
            iid=self.record.iid,
            Data_Set_Id=self.record.Data_Set_Id,
        )
        if volume_id:
            self.__url = url_build + f"&volumeid={volume_id}"
        else:
            self.__url = url_build

    def _find_volume_desc_url(self) -> str:
        """Find the URL volume description by parsing the ODE URL.

        The volume description contains all the references to the interesting catalogs to parse.

        Raises:
            NoFileExistInFolder: voldesc.cat file not found in PDS catalog

        Returns:
            str: the Volume description URL
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
        logger.info(f"voldesc.cat found in {vol_desc_url}")
        return vol_desc_url

    def _find_volume_id(self) -> str:
        """Find volume_id in web page

        Raises:
            NoFileExistInFolder: Volume_id not found

        Returns:
            str: volume_id
        """
        self._build_url_ode_collection()
        crawler = Crawler(self.url)
        links = crawler.parse()
        volume_id = None
        for link in links:
            if link["name"] == self.record.PDSVolume_Id:
                url: str = link["url"]
                parsed_url = urlparse(url)
                volume_id = parse_qs(parsed_url.query)["volumeid"][0]
                break
        if volume_id is None:
            raise NoFileExistInFolder(f"volumeid not found in {self.url}")
        logger.info(f"volume_id found : {volume_id}")
        return volume_id

    def _parse_volume_desc_cat(self) -> VolumeModel:
        """Set the volume description file by parsing the ODE URL.

        Raises:
            PdsCatalogDescriptionError: Error when getting or parsing the volume description file

        Returns:
            VolumeModel: the Volume description object
        """
        with closing(
            requests_retry_session().get(
                self.volume_desc_url, stream=True, verify=False, timeout=5
            )
        ) as request:
            if request.ok:
                content = request.text
                vol_desc_cat = PdsParserFactory.parse(
                    uri=content,
                    type_file=PdsParserFactory.FileGrammary.VOL_DESC,
                )
                return vol_desc_cat
            else:
                raise PdsCatalogDescriptionError(
                    f"Error when getting or parsing {self.volume_desc_url}"
                )

    def _load_volume_description(self):
        """Load the volume description."""
        try:
            self.__volume_desc_url: str = self._find_volume_desc_url()
        except NoFileExistInFolder:
            volume_id = self._find_volume_id()
            self._build_url_ode_collection(volume_id=volume_id)
            self.__volume_desc_url: str = self._find_volume_desc_url()
        self.__vol_desc_cat: VolumeModel = self._parse_volume_desc_cat()

    def _find_catalogs_urls(self) -> List[Dict[str, str]]:
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
        """Returns the URL of the catalog name that is contained in catalogs_from_desc_cat

        Args:
            catalog_name (str): catalog name
            catalogs_from_desc_cat (Dict[str, str]): list of catalogs

        Returns:
            List[str]: the URL of the catalog name
        """
        url_list: List[str] = list()
        catalog_name_lower: str = catalog_name.lower()
        if catalog_name_lower in catalogs_from_desc_cat:
            url: str = catalogs_from_desc_cat[catalog_name_lower]
            url_list.append(url)
        else:
            logger.error(f"Cannot find {catalog_name_lower} catalog")
        return url_list

    def _get_urls_from_catalog_type(
        self,
        catalog_type: Union[str, List[str]],
        catalogs_from_desc_cat: Dict[str, str],
    ) -> List[str]:
        """Returns the URLs of the catalog type that is contained in catalogs_from_desc_cat

        A catalog type can be associated to one or several catalogs.
        The list of catalogs (URL included) is provided by catalogs_from_desc_cat

        Args:
            catalog_type (Union[str, List[str]]): catalog type
            catalogs_from_desc_cat (Dict[str, str]): list of catalogs

        Returns:
            List[str]: _description_
        """
        url_list: List[str] = list()
        if self._is_catalog_exists(catalog_type):
            if isinstance(catalog_type, list):
                url_list.extend(
                    self._get_url_for_multiple_catalogs(
                        catalog_type, catalogs_from_desc_cat
                    )
                )
            else:
                url_list.extend(
                    self._get_url_for_simple_catalog(
                        catalog_type, catalogs_from_desc_cat
                    )
                )
        return url_list

    def _get_urls_from_volume_catalog(self) -> List[str]:
        """Get catalog URLs associated of the catalogs in the Volume catalog.

        Returns:
            List[str]: List of URLs
        """
        self._build_url_ode_collection(volume_id=self.record.PDSVolume_Id)

        # Extract the Volume description catalog
        # that contains an index of all catalogs
        self._load_volume_description()

        # Find all the catalogs in the catalog directory of ODE
        catalog_urls: List[Dict[str, str]] = self._find_catalogs_urls()
        mapping_file_url: Dict[str, str] = {
            catalog["name"]: catalog["url"] for catalog in catalog_urls
        }

        # Make the mapping beween catalog_type from Volume description catalog
        # and the catalogs found in catalog directory
        # In the volume description catalog, it is possible to have several
        # catalogs related to one catalog type.
        url_list: List[str] = list()
        catalog: CatalogModel = self.vol_desc_cat.CATALOG
        catalog_dict: Dict[str, str] = catalog.__dict__
        for key in catalog_dict.keys():
            url_list.extend(
                self._get_urls_from_catalog_type(
                    catalog_dict[key], mapping_file_url
                )
            )
        return url_list

    def _parse_catalog(
        self,
        file_storage: PdsCollectionStorage,
        catalog_name: str,
        cat_type: str,
        result: Dict[str, Union[str, List[str]]],
        timeout: int = 30,
    ):
        """Parses the PDS object (`catalog_name`), represented by a catalog type and stored
        on the file storage with a specific implementation associated to the catalog_type.

        The catalog is parsed by using the `get_catalog`method from the PdsStorage
        object. The result is then stored in result variable where the key is the `catalog_type`.
        At each `catalog_type` is associated one or several catalogs.

        If the parsing is not successful, the eror message is notified by the use of MessageModel
        object.

        Args:
            file_storage (PdsCollectionStorage): storage where the PDS objects have been downloaded
            catalog_name (str): catalog name that must be parsed
            cat_type (str): Type of catalog where an implementation is associated
            result (Dict[str, Union[str, List[str]]]): the catalogs in the Volume description
            timeout (int, optional): parser timeout in seconds. Defaults to 30
        """
        try:
            cat_obj = file_storage.get_catalog(
                file=catalog_name,
                catalogue_type=PdsParserFactory.FileGrammary.get_enum_from(cat_type),  # type: ignore
                timeout=timeout,
            )
            if cat_type in result:
                cast(List, result[cat_type]).append(cat_obj)
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

    def load_catalogs_urls(
        self, pds_collection: PdsRegistryModel, progress_bar: bool = True
    ):
        """Loads the catalogs URLs from cache for a given
        `pds_collection` collection.

        Args:
            pds_collection (PdsRegistryModel): PDS collection
            progress_bar (bool, True): Set progress_bar. Defaults to True.
        """
        self._initialize_values()
        self.__pds_collection = pds_collection
        records_iter: Iterator[
            PdsRecordsModel
        ] = self.pds_records.parse_pds_collection_from_cache(
            pds_collection,
            progress_bar=progress_bar,
        )
        try:
            records: PdsRecordsModel = next(records_iter)
            self.__record = records.pds_records_model[0]
            try:
                self.__catalogs_urls: List[
                    str
                ] = self._get_urls_from_volume_catalog()
            except NoFileExistInFolder as err:
                logger.exception(f"[NoFileExistInFolder]: {err}")
                self.notify_observers(MessageModel(str(pds_collection), err))
            except UnexpectedCharacters as err:
                logger.exception(f"[ParserError]: {err}")
                self.notify_observers(MessageModel(str(pds_collection), err))
            except ConnectionError as err:
                logger.exception(f"[ConnectionError]: {err}")
                self.notify_observers(MessageModel(str(pds_collection), err))
        except StopIteration:
            logger.error(
                f"No record for {pds_collection}. Please download them"
            )
            self.notify_observers(
                MessageModel(str(pds_collection), Exception("No record"))
            )
        except JSONDecodeError:
            logger.error(
                f"[CorruptedFile] Please remove the file corresponding to this collection {pds_collection}"
            )
            self.notify_observers(
                MessageModel(
                    str(pds_collection),
                    Exception("[CorruptedFile] Please remove the file"),
                )
            )

    def get_ode_catalogs(
        self, pds_collection: PdsRegistryModel, timeout: int = 30
    ) -> Dict[str, Any]:
        """Returns the PDS objects for a given space mission collection.

        The function retrieves the PdsStorage object associated
        with the PdsRegistryModel using get_pds_storage_for(), and then
        retrieves the description of the volume containing the PDS objects with
        get_volume_description(). It then lists the different types of catalogs
        in the directory using list_catalogs(), and for each catalog, it uses
        _parse_catalog() to retrieve information on each catalog.

        Args:
            pds_collection (PdsRegistryModel): the space mission collection
            timeout (int): parser timeout in seconds. Default to 30

        Raises:
            TypeError: Illegal datatype for catalog

        Returns:
            Dict[str, Any]: list of PDS Object name and its object
        """
        result = dict()
        result["collection"] = pds_collection
        try:
            file_storage: PdsCollectionStorage = (
                self.database.pds_storage.get_pds_storage_for(pds_collection)
            )
            result[
                PdsParserFactory.FileGrammary.VOL_DESC.name
            ] = file_storage.get_volume_description(timeout)
            catalogs = file_storage.list_catalogs()
            for cat_type in catalogs.keys():
                catalog_value: Union[str, List[str]] = catalogs[cat_type]
                if catalog_value is None:
                    continue
                elif isinstance(catalog_value, str):
                    catalog_name: str = catalog_value
                    self._parse_catalog(
                        file_storage, catalog_name, cat_type, result, timeout
                    )
                elif isinstance(catalog_value, list):
                    result[cat_type] = list()
                    for catalog_name in catalog_value:
                        self._parse_catalog(
                            file_storage,
                            catalog_name,
                            cat_type,
                            result,
                            timeout,
                        )
                else:
                    raise TypeError(
                        f"Illegal datatype for catalog : {type(catalog_value)}"
                    )

            return result
        except FileNotFoundError as err:
            logger.exception(err)
            return result

    def __repr__(self) -> str:
        return f"PDSCatalogDescription({self.pds_records})"


class PDSCatalogsDescription(Observable):
    """Provides the means to download the PDS catalogs (PDS objects).

    .. uml::

        class PDSCatalogsDescription {
            - Any report
            + Database database
            + PDSCatalogDescription pds_object_cats
            - build_all_urls(pds_collection: PdsRegistryModel) List[str]
            + download(pds_collections: List[PdsRegistryModel])
            + get_ode_catalogs(pds_collections: List[PdsRegistryModel]) -> Iterator[Dict[str, Any]]
            + __repr__(self) str
        }
    """

    def __init__(self, database: Database, *args, **kwargs):
        """Initialize the means to download by using a database to store the results.

        Args:
            database (Database): database
        """
        super().__init__()
        if kwargs.get("report"):
            self.__report = kwargs.get("report")
            self.subscribe(self.__report)
        self.__pds_object_cats = PDSCatalogDescription(
            database, *args, **kwargs
        )
        self.__database = database

    @property
    def pds_object_cats(self) -> PDSCatalogDescription:
        return self.__pds_object_cats

    @property
    def database(self) -> Database:
        return self.__database

    def _build_all_urls(
        self, pds_collection: PdsRegistryModel, progress_bar: bool = True
    ) -> List[str]:
        """Builds all the PDS objects URLs for collections of space missions.

        These URLs are used to retrieve all PDS objects.

        Args:
            pds_collection (PdsRegistryModel): the collections of space missions
            progress_bar (bool, True): Set progress_bar. Defaults to True.

        Returns:
            List[str]: List of URLs
        """
        logger.info(f"Fetching Catalogs URLs from {pds_collection}")
        urls_list: List[str] = list()
        self.pds_object_cats.load_catalogs_urls(pds_collection, progress_bar)
        urls: List[str] = self.pds_object_cats.catalogs_urls
        if len(urls) != 0:
            urls_list.extend(urls)
            urls_list.append(self.pds_object_cats.volume_desc_url)
        return urls_list

    def download(
        self,
        pds_collections: List[PdsRegistryModel],
        nb_workers: int = 3,
        time_sleep: int = 1,
        progress_bar: bool = True,
    ):
        """Downloads the PDS objects for the collections of space missions.

        This method is responsible for downloading the PDS objects for the given
        collections of space missions. It does so by building a list of URLs of
        PDS objects, creating a PdsStorage instance for the given
        collection, and using the parallel_requests method to download each PDS object.
        The parallel_requests function is likely using threading or multiprocessing to
        download the objects in parallel, which is a good optimization to speed up the
        download process.

        Args:
            pds_collections (List[PdsRegistryModel]): the collections of space missions
            nb_workers (int, optional): Number of workers in parallel. Defaults to 3.
            time_sleep (int, optional): Time to way between two download series. Defaults to 1.
            progress_bar (bool, True): Set progress_bar. Defaults to True.
        """
        for pds_collection in pds_collections:
            urls_list: List[str] = self._build_all_urls(
                pds_collection, progress_bar
            )
            try:
                file_storage: PdsCollectionStorage = (
                    self.database.pds_storage.get_pds_storage_for(
                        pds_collection
                    )
                )
                file_storage.download(
                    urls=urls_list,
                    nb_workers=nb_workers,
                    timeout=5,
                    time_sleep=time_sleep,
                    progress_bar=progress_bar,
                )
            except UnexpectedCharacters as err:
                logger.exception(f"[ParserError]: {err}")
            except ConnectionError as err:
                logger.exception(f"[ConnectionError]: {err}")

    def get_ode_catalogs(
        self, pds_collections: List[PdsRegistryModel], timeout: int = 30
    ) -> Iterator[Dict[str, Any]]:
        """Get all the PDS objects for the `pds_collections`.

        This class PDSCatalogsDescription provides the means to download the
        PDS catalogs for the PDS collections. It has three main
        methods:
        1. _build_all_urls(): Builds all the PDS object URLs for a given collection
        of space missions. This method is used to retrieve all the PDS objects of a
        collection.
        2. download(): Downloads the PDS objects for the PDS collections.
        It takes a list of PdsRegistryModel as input and downloads the PDS objects for
        each collection.
        3. get_ode_catalogs(): Gets all the PDS objects for a list of collections of
        space missions. It takes a list of PdsRegistryModel as input and returns an
        iterator that yields a dictionary containing the PDS object name and its object.
        The method internally calls the get_ode_catalogs() method of the PDSCatalogDescription
        class, which retrieves the PDS objects for a given collection.

        Args:
            pds_collections (List[PdsRegistryModel]): the collections of the space mission.
            timeout (int, optional): parser timeout in seconds. Defaults to 30

        Yields:
            Iterator[Dict[str, Any]]: PDS object name and its object
        """
        for pds_collection in pds_collections:
            yield self.pds_object_cats.get_ode_catalogs(
                pds_collection, timeout
            )
