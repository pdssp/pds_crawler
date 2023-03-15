# -*- coding: utf-8 -*-
import os
import shutil
from os.path import abspath
from os.path import dirname

import pytest

from pds_crawler.etl import StacETL
from pds_crawler.load import Database
from pds_crawler.models import PdsRegistryModel
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


@pytest.fixture
def stac_records_transformer():
    # create an instance of the StacRecordsTransformer class
    return StacRecordsTransformer(Database(result_dir))


@pytest.fixture
def stac_etl():
    # create an instance of the stac_etl class
    return StacETL(result_dir)


def test_check_collections_to_ingest(stac_etl):
    # create some sample input
    cached_pds_collections = [
        PdsRegistryModel(
            ODEMetaDB="mars",
            IHID="platforme",
            IHName="plateforme",
            IID="instrument",
            IName="instrment",
            PT="image",
            PTName="image",
            DataSetId="col1",
            NumberProducts=10,
            ValidTargets={"target": ["Mars"]},
        ),
        PdsRegistryModel(
            ODEMetaDB="mars",
            IHID="platforme",
            IHName="plateforme",
            IID="instrument",
            IName="instrment",
            PT="image",
            PTName="image",
            DataSetId="col2",
            NumberProducts=10,
            ValidTargets={"target": ["Mars"]},
        ),
        PdsRegistryModel(
            ODEMetaDB="mars",
            IHID="platforme",
            IHName="plateforme",
            IID="instrument",
            IName="instrment",
            PT="image",
            PTName="image",
            DataSetId="col3",
            NumberProducts=10,
            ValidTargets={"target": ["Mars"]},
        ),
    ]

    # call the method with the sample input
    result = stac_etl._check_collections_to_ingest(cached_pds_collections)

    # check the output against the expected value
    assert result == 3  # we expect all collections to be ingested


def test__check_updates_from_PDS(stac_etl):
    pds_collections = [
        PdsRegistryModel(
            ODEMetaDB="mars",
            IHID="platforme",
            IHName="plateforme",
            IID="instrument",
            IName="instrment",
            PT="image",
            PTName="image",
            DataSetId="col1",
            NumberProducts=10,
            ValidTargets={"target": ["Mars"]},
        ),
        PdsRegistryModel(
            ODEMetaDB="mars",
            IHID="platforme",
            IHName="plateforme",
            IID="instrument",
            IName="instrment",
            PT="image",
            PTName="image",
            DataSetId="col2",
            NumberProducts=12,
            ValidTargets={"target": ["Mars"]},
        ),
        PdsRegistryModel(
            ODEMetaDB="mars",
            IHID="platforme",
            IHName="plateforme",
            IID="instrument",
            IName="instrment",
            PT="image",
            PTName="image",
            DataSetId="col3",
            NumberProducts=10,
            ValidTargets={"target": ["Mars"]},
        ),
    ]
    pds_collections_cache = [
        PdsRegistryModel(
            ODEMetaDB="mars",
            IHID="platforme",
            IHName="plateforme",
            IID="instrument",
            IName="instrment",
            PT="image",
            PTName="image",
            DataSetId="col2",
            NumberProducts=10,
            ValidTargets={"target": ["Mars"]},
        )
    ]
    nb_to_update = stac_etl._check_updates_from_PDS(
        pds_collections, pds_collections_cache
    )
    assert nb_to_update == 1
