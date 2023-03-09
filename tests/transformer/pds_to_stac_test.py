# -*- coding: utf-8 -*-
import os
import shutil
from os.path import abspath
from os.path import dirname

import pytest

from pds_crawler.extractor import PDSCatalogsDescription
from pds_crawler.extractor import PdsRecordsWs
from pds_crawler.extractor import PdsRegistry
from pds_crawler.load import Database
from pds_crawler.transformer import StacCatalogTransformer
from pds_crawler.transformer import StacRecordsTransformer

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


def test_catalog_transformation():
    database = Database(result_dir)

    # Get the list of collections
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        body="mars", dataset_id="mro-m-ctx-2-edr-l0-v1.0"
    )

    # Download records from the collections
    pds_records = PdsRecordsWs(database)
    pds_records.download_pds_records_for_all_collections(collections, limit=1)

    # Download PDS3 objects from the collections
    catalogs = PDSCatalogsDescription(database)
    catalogs.download(collections)

    # transform
    stac_catalog_transformer = StacCatalogTransformer(database)
    stac_catalog_transformer.init()
    stac_catalog_transformer.to_stac(catalogs, collections)
    stac_catalog_transformer.save()
    database.stac_storage.refresh()
    root_catalog = database.stac_storage.root_catalog
    assert root_catalog is not None


def test_collection_transformation():
    database = Database(result_dir)

    # Get the list of collections
    pds_registry = PdsRegistry(database)
    _, collections = pds_registry.get_pds_collections(
        body="mars", dataset_id="mro-m-ctx-2-edr-l0-v1.0"
    )

    # Download records from the collections
    pds_records = PdsRecordsWs(database)
    pds_records.download_pds_records_for_all_collections(collections, limit=2)

    # Download PDS3 objects from the collections
    catalogs = PDSCatalogsDescription(database)
    catalogs.download(collections)

    # Transform catalogs
    stac_catalog_transformer = StacCatalogTransformer(database)
    stac_catalog_transformer.init()
    stac_catalog_transformer.to_stac(catalogs, collections)
    stac_catalog_transformer.save()
    database.stac_storage.refresh()

    # Transform items
    stac_records_transformer = StacRecordsTransformer(database)
    stac_records_transformer.init()
    stac_records_transformer.load_root_catalog()
    stac_records_transformer.to_stac(pds_records, collections)
    stac_records_transformer.save()

    stac_collection = stac_records_transformer.catalog.get_child(
        id=collections[0].get_collection_id(), recursive=True
    )
    assert stac_collection is not None
    number_items = len(list(stac_collection.get_items()))
    assert number_items > 0
