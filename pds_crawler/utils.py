# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
import concurrent.futures
import logging
import os
import time
from datetime import datetime
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Any
from typing import Dict
from typing import List
from urllib.parse import parse_qs
from urllib.parse import urlparse

import requests
from fastnumbers import float as ffloat
from fastnumbers import int as iint
from fastnumbers import isfloat
from fastnumbers import isint
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3 import Retry

from .exception import DateConversionError

logger = logging.getLogger(__name__)

requests.urllib3.disable_warnings(
    requests.urllib3.exceptions.InsecureRequestWarning
)


class DocEnum(Enum):
    """Enum where we can add documentation."""

    def __new__(cls, value, doc=None):
        self = object.__new__(
            cls
        )  # calling super().__new__(value) here would fail
        self._value_ = value
        if doc is not None:
            self.__doc__ = doc
        return self


class GrammarEnum(Enum):
    """Enum where we can add documentation and grammar."""

    def __new__(cls, *args):
        obj = object.__new__(cls)
        obj._value_ = str(args[1])  # keep the value of the enum
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(  # pylint: disable=too-many-arguments
        self,
        value: str,
        grammar: str,
        class_name: str,
        doc=None,
    ):
        self._grammar_: str = grammar
        self._class_name_: str = class_name
        if doc is not None:
            self.__doc__ = doc

    @property
    def grammar(self) -> str:
        return self._grammar_

    @property
    def class_name(self) -> str:
        return self._class_name_


class UtilsMath:
    def is_integer(value: str) -> bool:
        return isint(value)

    def is_float(value: str) -> bool:
        return isfloat(str)

    def is_bool(value: str) -> bool:
        if not isinstance(value, str):
            return False
        return value.lower() in [
            "true",
            "t",
            "y",
            "yes",
            "false",
            "f",
            "n",
            "no",
        ]

    def convert_dt(value: str) -> Any:
        result: Any
        if not isinstance(value, str):
            result = value
        elif isint(value):
            result = int(value)
        elif isfloat(value):
            result = ffloat(value)
        elif UtilsMath.is_bool(value):
            result = bool(value)
        else:
            result = value
        return result


def timeit(func):
    """Decorator to measure the time spent in an function"""

    @wraps(func)
    def timeit_wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        total_time = end_time - start_time
        logger.info(
            f"Function {func.__name__}{args} {kwargs} Took {total_time:.4f} seconds"
        )
        return result

    return timeit_wrapper


def cache_download(func):
    """Decorator parallel_requests to check if the download has been done."""

    @wraps(func)
    def cache_download_wrapper(*args, **kwargs):
        if func.__name__ != "parallel_requests":
            raise NotImplementedError()
        directory: str = args[0]
        urls: List[str] = args[1]
        urls_copy: List[str] = urls.copy()
        for url in urls:
            filepath: str = compute_downloaded_filepath(directory, url)
            if os.path.exists(filepath):
                logger.warning(f"file {filepath} in cache, skip the download")
                urls_copy.remove(url)
            else:
                logger.info(f"Downloading {url} in progress")
        if len(args) == 3:
            new_args = (args[0], urls_copy, args[2])
        else:
            new_args = (args[0], urls_copy)
        result = func(*new_args, **kwargs)
        return result

    return cache_download_wrapper


def requests_retry_session(
    retries=3,
    backoff_factor=3,
    status_forcelist=(500, 502, 504),
    session=None,
) -> requests.Session:
    """Requests with retry

    A backoff factor to apply between attempts after the second try (most errors are resolved immediately by a
    second try without a delay). The request will sleep for
    {backoff factor} * (2 ** ({number of total retries} - 1))

    Args:
        retries (int, optional): number of retries. Defaults to 3.
        backoff_factor (int, optional): backoff factor. Defaults to 3.
        status_forcelist (tuple, optional): status for which the retry must be done. Defaults to (500, 502, 504).
        session (_type_, optional): http/https session. Defaults to None.

    Returns:
        requests.Session: session
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def simple_download(url: str, filepath: str, timeout):
    response = requests.get(
        url, allow_redirects=True, verify=False, timeout=timeout
    )
    outfile = Path(filepath)
    outfile.write_bytes(response.content)


@cache_download
def parallel_requests(
    directory: str,
    urls: List[str],
    nb_workers: int = 3,
    timeout=180,
    time_sleep=2,
):
    def scrape(url):
        start = time.time()
        filepath: str = compute_downloaded_filepath(directory, url)
        with requests_retry_session():
            simple_download(url, filepath, timeout)
            time.sleep(time_sleep)
        end = time.time()
        hours, rem = divmod(end - start, 3600)
        minutes, seconds = divmod(rem, 60)
        file_size_bytes = os.path.getsize(filepath)
        file_size_mb = file_size_bytes / 1024**2
        tqdm.write(
            f"{url} downloaded ({file_size_mb:0.03f} MB) in {int(hours):0>2}:{int(minutes):0>2}:{seconds:05.2f}"
        )
        return url

    if len(urls) == 0:
        return

    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    pbar = tqdm(total=len(urls), desc="Downloading data", position=1)

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=nb_workers
    ) as executor:
        futures = [executor.submit(scrape, url) for url in urls]
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except requests.exceptions.ConnectionError as err:
                logger.exception(f"[parallel_requests]: {err}")
            pbar.update(n=1)

    pbar.close()


def compute_downloaded_filepath(directory: str, url: str) -> str:
    parsed_url = urlparse(url)
    params: Dict[str, str] = parse_qs(parsed_url.query)
    filename: str
    if "ihid" in params:
        filename = f"{params['target'][0]}_{params['ihid'][0]}_{params['iid'][0]}_{params['pt'][0]}_{params['offset'][0]}.json"
        filename = filename.replace(os.path.sep, "_")
    else:
        path: str = parsed_url.path
        filename: str = os.path.basename(path)
    return os.path.join(directory, filename)


def compute_download_directory_path(
    directory: str, target: str, ihid: str, iid: str, pt: str, ds: str
) -> str:
    items = [
        item.lower().replace(os.path.sep, "_")
        for item in [target, ihid, iid, pt, ds]
    ]
    return os.path.join(directory, os.path.sep.join(items))


def inverse_mapping(f):
    mapping = dict()
    for item in f.items():
        keyword = item[0]
        val = item[1]
        if isinstance(val, list):
            for elt in val:
                mapping[elt] = keyword
        else:
            mapping[val] = keyword
    return mapping


def utc_to_iso(utc_time, timespec="auto"):
    """Convert UTC time string to ISO format string (STAC standard)."""
    # set valid datatime formats 2018-08-23T23:24:36.865Z
    valid_formats = [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d",
    ]
    for valid_format in valid_formats:
        try:
            return datetime.strptime(utc_time, valid_format).isoformat(
                timespec=timespec
            )
        except:  # noqa: E722
            continue
    raise DateConversionError(
        f"Cannot convert in ISO str this time {utc_time} with the following patterns {valid_formats}"
    )


class Observable:
    """Observable"""

    def __init__(self):
        """Init the observable"""
        self._observers = list()

    def subscribe(self, observer):
        """Subscribe the observable to the observer

        Args:
            observer (Observer): Observer
        """
        self._observers.append(observer)

    def notify_observers(self, *args, **kwargs):
        """Notify the observers"""
        for obs in self._observers:
            obs.notify(self, *args, **kwargs)

    def unsubscribe(self, observer):
        """Unsubscribe the observers

        Args:
            observer (Observer): Observer
        """
        self._observers.remove(observer)

    def unsubscribe_all(self):
        """Unsubscribe all observers."""
        self._observers.clear()


class Observer:  # pylint: disable=R0903
    """Observer"""

    def __init__(self, observable):
        """Init the observer

        Args:
            observable (Observable): Observable to observe
        """
        observable.subscribe(self)

    def notify(self, observable, *args, **kwargs):  # pylint: disable=R0201
        """Notify

        Args:
            observable (Observable): Observable
        """
        print("Got", args, kwargs, "From", observable)
