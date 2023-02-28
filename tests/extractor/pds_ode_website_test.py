# -*- coding: utf-8 -*-
import os
import shutil
from os.path import abspath
from os.path import dirname
from typing import Optional

import pytest

from pds_crawler.extractor import PDSCatalogDescription
from pds_crawler.extractor import PdsRecordsWs
from pds_crawler.extractor import PdsRegistry
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


def test_load_catalogs_urls():
    database = Database(result_dir)
    pds_records = PdsRecordsWs(database)
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        planet="mars", dataset_id="mro-m-ctx-2-edr-l0-v1.0"
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
        planet="mars", dataset_id="mro-m-ctx-2-edr-l0-v1.0"
    )
    pds_records.download_pds_records_for_all_collections(collections, limit=1)
    catalog = PDSCatalogDescription(database)
    catalog.load_catalogs_urls(collections[0])
    catalogs = catalog.get_ode_catalogs(collections[0])
    assert len(catalogs) > 0
