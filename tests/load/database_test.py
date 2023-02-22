# -*- coding: utf-8 -*-
import os
import shutil
from os.path import abspath
from os.path import dirname

import pytest

from pds_crawler.extractor import PdsRegistry
from pds_crawler.load import Database

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


def test_create_default_database():
    database = Database(result_dir)
    assert database.base_directory == result_dir
    assert os.path.exists(os.path.join(result_dir, "pds.h5"))
    assert os.path.exists(os.path.join(result_dir, "files"))
    assert os.path.exists(os.path.join(result_dir, "stac"))


def test_delete_database():
    database = Database(result_dir)
    database.reset_storage()
    assert database.base_directory == result_dir
    assert not os.path.exists(os.path.join(result_dir, "pds.h5"))
    assert not os.path.exists(os.path.join(result_dir, "files"))
    assert not os.path.exists(os.path.join(result_dir, "stac"))


def test_create_custom_database():
    database = Database(result_dir)
    database.reset_storage()
    database.hdf5_name = "test.h5"
    database.pds_dir = "pds_test"
    database.stac_dir = "stac_test"
    database.init_storage()
    assert os.path.exists(os.path.join(result_dir, "test.h5"))
    assert os.path.exists(os.path.join(result_dir, "pds_test"))
    assert os.path.exists(os.path.join(result_dir, "stac_test"))


def test_hdf5_storage():
    database = Database(result_dir)
    pds = PdsRegistry(database)
    stats, mars_coll = pds.get_pds_collections("mars")
    database.hdf5_storage.save_collections(mars_coll)
    mars_coll2 = database.hdf5_storage.load_collections("mars")
    assert mars_coll == mars_coll2


def test_hdf5_avoid_duplication():
    database = Database(result_dir)
    pds = PdsRegistry(database)
    stats, mars_coll = pds.get_pds_collections("mars")
    is_save1 = database.hdf5_storage.save_collections(mars_coll)
    is_save2 = database.hdf5_storage.save_collections(mars_coll)
    assert is_save1
    assert not is_save2
