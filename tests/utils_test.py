# -*- coding: utf-8 -*-
import os
import shutil
import signal
import tempfile
import time
from os.path import abspath
from os.path import dirname
from typing import List
from typing import Optional
from unittest.mock import patch

import pytest
from requests.exceptions import RetryError

from pds_crawler.utils import cache_download
from pds_crawler.utils import Locking
from pds_crawler.utils import parallel_requests
from pds_crawler.utils import UtilsMath

root_dir = dirname(dirname(abspath(__file__)))
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


def test_is_integer():
    assert UtilsMath.is_integer("123") is True
    assert UtilsMath.is_integer("-456") is True
    assert UtilsMath.is_integer("123.4") is False
    assert UtilsMath.is_integer("abc") is False


def test_is_float():
    assert UtilsMath.is_float("123.45") is True
    assert UtilsMath.is_float("-456.78") is True
    assert UtilsMath.is_float("123") is False
    assert UtilsMath.is_float("abc") is False


def test_is_bool():
    assert UtilsMath.is_bool("true") is True
    assert UtilsMath.is_bool("t") is True
    assert UtilsMath.is_bool("yes") is True
    assert UtilsMath.is_bool("1") is False
    assert UtilsMath.is_bool("abc") is False


def test_convert_dt():
    assert UtilsMath.convert_dt("123") == 123
    assert UtilsMath.convert_dt("123.45") == 123.45
    assert UtilsMath.convert_dt("true") is True
    assert UtilsMath.convert_dt("false") is False
    assert UtilsMath.convert_dt("abc") == "abc"


# Test parallel_requests with a single URL
def test_parallel_requests_single_url():
    with tempfile.TemporaryDirectory() as tmp_dir:

        def timeout_handler(signum, frame):
            raise TimeoutError("too long!")

        urls = ["https://httpbin.org/uuid"]
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
        count = 0
        while count != 1:
            try:
                parallel_requests(tmp_dir, urls)
                count = 0
                for path in os.listdir(tmp_dir):
                    # check if current path is a file
                    if os.path.isfile(os.path.join(tmp_dir, path)):
                        count += 1
                time.sleep(1)
            except TimeoutError:
                pass
            finally:
                signal.alarm(0)
        assert count == 1


# Test parallel_requests with multiple URLs
def test_parallel_requests_multiple_urls():
    with tempfile.TemporaryDirectory() as tmp_dir:

        def timeout_handler(signum, frame):
            raise TimeoutError("too long!")

        urls = [
            "https://httpbin.org/uuid",
            "https://httpbin.org/user-agent",
            "https://httpbin.org/headers",
        ]
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(10)
        count = 0
        while count != 3:
            try:
                parallel_requests(tmp_dir, urls)
                count = 0
                for path in os.listdir(tmp_dir):
                    # check if current path is a file
                    if os.path.isfile(os.path.join(tmp_dir, path)):
                        count += 1
                time.sleep(1)
            except TimeoutError:
                pass
            finally:
                signal.alarm(0)

        assert count == 3


def test_lock_file_creates_lock_file():
    # Arrange
    filename = os.path.join(result_dir, "test.txt")
    lock_filename = filename + ".lock"

    # Act
    Locking.lock_file(filename)

    # Assert
    assert os.path.exists(lock_filename)

    # Cleanup
    os.rmdir(lock_filename)


def test_lock_file_blocks_access_to_file():
    def timeout_handler(signum, frame):
        raise TimeoutError("too long!")

    # Arrange
    filename = os.path.join(result_dir, "test.txt")
    lock_filename = filename + ".lock"
    Locking.lock_file(filename)
    open(filename, "w").close()

    # Act
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(2)
    try:
        Locking.lock_file(filename)
    except TimeoutError:
        assert True
    finally:
        signal.alarm(0)

    # Assert
    assert os.path.exists(lock_filename)

    # Cleanup
    os.remove(filename)
    os.rmdir(lock_filename)


def test_unlock_file_removes_lock_file():
    # Arrange
    filename = os.path.join(result_dir, "test.txt")
    lock_filename = filename + ".lock"
    Locking.lock_file(filename)
    open(filename, "w").close()

    # Act
    Locking.unlock_file(filename)

    # Assert
    assert not os.path.exists(lock_filename)
