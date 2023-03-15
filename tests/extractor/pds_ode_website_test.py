# -*- coding: utf-8 -*-
import os
import shutil
from os.path import abspath
from os.path import dirname
from typing import Optional
from unittest.mock import patch

import pytest
from bs4 import BeautifulSoup

from pds_crawler.exception import NoFileExistInFolder
from pds_crawler.extractor import PDSCatalogDescription
from pds_crawler.extractor import PdsRecordsWs
from pds_crawler.extractor import PdsRegistry
from pds_crawler.extractor.pds_ode_website import Crawler
from pds_crawler.load import Database
from pds_crawler.models import PdsRecordsModel

root_dir = os.path.join(dirname(dirname(abspath(__file__))), "..")
test_dir = os.path.join(root_dir, "tests")
result_dir = os.path.join(test_dir, "results")


@pytest.fixture(autouse=True)
def my_setup_and_tear_down():
    # SETUP
    setup_directory()
    yield
    # TEARDOWN
    teardown_directory()


def setup_directory():
    os.makedirs(result_dir, exist_ok=True)


def teardown_directory():
    shutil.rmtree(result_dir)


# Test that is_file returns True for files and False for folders
def test_is_file():
    assert Crawler.is_file("http://example.com/file.txt") is True
    assert Crawler.is_file("http://example.com/folder") is False


# Test that _get_subdirs_file returns links and names of subfolders and files
def test_get_subdirs_file():
    soup = BeautifulSoup(
        """
        <table>
            <tr><td><a href="http://example.com/folder1">Folder 1</a></td></tr>
            <tr><td><a href="http://example.com/file1.txt">File 1</a></td></tr>
        </table>
    """,
        "html.parser",
    )
    assert Crawler("http://example.com")._get_subdirs_file(soup) == [
        {"url": "http://example.com/folder1", "name": "Folder 1"},
        {"url": "http://example.com/file1.txt", "name": "File 1"},
    ]


# Test that _get_content raises an exception if no file exists in the folder
@patch("pds_crawler.extractor.pds_ode_website.Crawler.query")
def test_get_content_no_files(mock_query):
    mock_query.return_value = "No files exist in this folder"
    with pytest.raises(NoFileExistInFolder):
        Crawler("http://example.com")._get_content(
            "http://example.com", "folder"
        )


def test_load_catalogs_urls():
    database = Database(result_dir)
    pds_records = PdsRecordsWs(database)
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        body="mars", dataset_id="mro-m-ctx-2-edr-l0-v1.0"
    )
    pds_records.download_pds_records_for_all_collections(collections, limit=1)
    catalog = PDSCatalogDescription(database)
    catalog.load_catalogs_urls(collections[0])
    assert len(catalog.catalogs_urls) > 0


def test_catalogs():
    database = Database(result_dir)
    pds_records = PdsRecordsWs(database)
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        body="mars", dataset_id="mro-m-ctx-2-edr-l0-v1.0"
    )
    pds_records.download_pds_records_for_all_collections(collections, limit=1)
    catalog = PDSCatalogDescription(database)
    catalog.load_catalogs_urls(collections[0])
    catalogs = catalog.get_ode_catalogs(collections[0])
    assert len(catalogs) > 0
