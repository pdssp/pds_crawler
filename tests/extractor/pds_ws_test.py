# -*- coding: utf-8 -*-
import os
import shutil
from os.path import abspath
from os.path import dirname
from typing import Optional

import pytest

from pds_crawler.extractor import PdsRecords
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


def test_pds_collections():
    database = Database(result_dir)
    pds_registry = PdsRegistry(database)
    stats, collections = pds_registry.get_pds_collections(
        planet="mercury", dataset_id="izenberg_pdart14_meap-data_tnmap"
    )
    collection = collections[0]
    assert collection.ODEMetaDB == "Mercury"
    assert collection.DataSetId == "izenberg_pdart14_meap-data_tnmap"
    assert collection.NumberProducts == 1


def test_pds_download():
    database = Database(result_dir)
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        planet="mercury", dataset_id="izenberg_pdart14_meap-data_tnmap"
    )
    pds_records = PdsRecords(database)
    pds_records.download_pds_records_for_all_collections(collections)
    files = database.pds_storage.get_pds_storage_for(
        collections[0]
    ).list_files()
    assert len(files) > 0


def test_cache_collections():
    database = Database(result_dir)
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        planet="mercury", dataset_id="izenberg_pdart14_meap-data_tnmap"
    )
    pds_registry.cache_pds_collections(collections)
    loaded_collections = pds_registry.load_pds_collections_from_cache(
        planet="mercury", dataset_id="izenberg_pdart14_meap-data_tnmap"
    )
    assert loaded_collections == collections


def test_pds_load():
    database = Database(result_dir)
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        planet="mercury", dataset_id="izenberg_pdart14_meap-data_tnmap"
    )
    pds_registry.cache_pds_collections(collections)

    pds_records: PdsRecords = PdsRecords(database)
    collections = pds_registry.load_pds_collections_from_cache(
        planet="mercury", dataset_id="izenberg_pdart14_meap-data_tnmap"
    )

    pds_records.download_pds_records_for_all_collections(collections)
    records: Optional[PdsRecordsModel] = None
    assert len(collections) > 0
    for collection in collections:
        for pds_records_model in pds_records.parse_pds_collection_from_cache(
            collection
        ):
            records = pds_records_model
    assert records is not None
    assert records.dataset_id == "izenberg_pdart14_meap-data_tnmap"


def test_query_cache():
    database = Database(result_dir)
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        planet="mercury", dataset_id="izenberg_pdart14_meap-data_tnmap"
    )
    pds_registry.cache_pds_collections(collections)
    loaded_collection = pds_registry.query_cache(
        "izenberg_pdart14_meap-data_tnmap"
    )
    assert loaded_collection is not None
    assert loaded_collection == collections[0]


def test_distinct_values():
    database = Database(result_dir)
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        planet="mercury", dataset_id="izenberg_pdart14_meap-data_tnmap"
    )
    pds_registry.cache_pds_collections(collections)
    dataset_ids = list(pds_registry.distinct_dataset_values())
    assert dataset_ids[0] == "izenberg_pdart14_meap-data_tnmap"
