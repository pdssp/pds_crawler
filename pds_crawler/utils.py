# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
import concurrent.futures
import logging
import os
import time
import tracemalloc
from datetime import datetime
from enum import Enum
from functools import partial
from functools import wraps
from pathlib import Path
from typing import Any
from typing import cast
from typing import Dict
from typing import List
from urllib.parse import parse_qs
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from bs4 import Tag
from fastnumbers import float as ffloat
from fastnumbers import int as iint
from fastnumbers import isfloat
from fastnumbers import isint
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3 import Retry

from .exception import DateConversionError

logger = logging.getLogger(__name__)
requests.urllib3.disable_warnings(  # type: ignore
    requests.urllib3.exceptions.InsecureRequestWarning  # type: ignore
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


class UtilsMath:
    @staticmethod
    def is_integer(value: str) -> bool:
        return isint(value)

    @staticmethod
    def is_float(value: str) -> bool:
        return isfloat(str)

    @staticmethod
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

    @staticmethod
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
    if response.status_code == 200:
        if "text/html" in response.headers.get("content-type", ""):
            soup = BeautifulSoup(response.content, "html.parser")
            redirect_elt = soup.find(
                "meta", attrs={"http-equiv": "refresh", "content": True}
            )
            if redirect_elt is not None:
                redirect_tag = cast(Tag, redirect_elt)
                redirect_tag_value: str = cast(str, redirect_tag["content"])
                redirect_url = (
                    redirect_tag_value.split(";")[1].strip().split("=")[1]
                )
                response = requests.get(
                    redirect_url,
                    allow_redirects=True,
                    verify=False,
                    timeout=timeout,
                )
        outfile: Path = Path(filepath)
        outfile.write_bytes(response.content)
    else:
        logger.error(
            f"The request {url} has failed with the error code: {response.status_code}"
        )


@cache_download
def parallel_requests(
    directory: str,
    urls: List[str],
    nb_workers: int = 3,
    timeout=180,
    time_sleep=2,
    progress_bar=False,
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

    pbar = tqdm(
        total=len(urls),
        desc="Downloading data",
        position=1,
        disable=not progress_bar,
    )

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
    params: Dict[str, str] = parse_qs(parsed_url.query)  # type: ignore
    filename: str
    if "ihid" in params:
        filename = f"{params['target'][0]}_{params['ihid'][0]}_{params['iid'][0]}_{params['pt'][0]}_{params['offset'][0]}.json"
        filename = filename.replace(os.path.sep, "_")
    else:
        path: str = parsed_url.path
        filename: str = os.path.basename(path).lower()
    return os.path.join(directory, filename)


def compute_download_directory_path(
    directory: str, target: str, ihid: str, iid: str, pt: str, ds: str
) -> str:
    items = [
        item.lower().replace(os.path.sep, "_")
        for item in [target, ihid, iid, pt, ds]
    ]
    return os.path.join(directory, os.path.sep.join(items))


def utc_to_iso(utc_time: str, timespec: str = "auto") -> str:
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


class UtilsMonitoring:  # noqa: R0205
    """Some Utilities."""

    # pylint: disable:invalid_name
    @staticmethod
    def io_display(
        func=None, input=True, output=True, level=15
    ):  # pylint: disable=W0622
        """Monitor the input/output of a function.

        NB : Do not use this monitoring method on an __init__ if the class
        implements __repr__ with attributes

        Parameters
        ----------
        func: func
            function to monitor (default: {None})
        input: bool
            True when the function must monitor the input (default: {True})
        output: bool
            True when the function must monitor the output (default: {True})
        level: int
            Level from which the function must log
        Returns
        -------
        object : the result of the function
        """
        if func is None:
            return partial(
                UtilsMonitoring.io_display,
                input=input,
                output=output,
                level=level,
            )

        @wraps(func)
        def wrapped(*args, **kwargs):
            name = func.__qualname__
            logger = logging.getLogger(__name__ + "." + name)

            if input and logger.getEffectiveLevel() >= level:
                msg = f"[{name}] Entering '{name}' (args={args}, kwargs={kwargs})"
                logger.log(level, msg)

            result = func(*args, **kwargs)

            if output and logger.getEffectiveLevel() >= level:
                msg = f"[{name}] Exiting '{name}' (result={result})"
                logger.log(level, msg)

            return result

        return wrapped

    @staticmethod
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

    @staticmethod
    def measure_memory(func=None, level=logging.DEBUG):
        """Measure the memory of the function

        Args:
            func (func, optional): Function to measure. Defaults to None.
            level (int, optional): Level of the log. Defaults to logging.INFO.

        Returns:
            object : the result of the function
        """
        if func is None:
            return partial(UtilsMonitoring.measure_memory, level=level)

        @wraps(func)
        def newfunc(*args, **kwargs):
            name = func.__qualname__
            logger = logging.getLogger(__name__ + "." + name)
            tracemalloc.start()
            result = func(*args, **kwargs)
            current, peak = tracemalloc.get_traced_memory()
            msg = f"""
            \033[37mFunction Name       :\033[35;1m {func.__name__}\033[0m
            \033[37mCurrent memory usage:\033[36m {current / 10 ** 6}MB\033[0m
            \033[37mPeak                :\033[36m {peak / 10 ** 6}MB\033[0m
            """
            logger.log(level, msg)
            tracemalloc.stop()
            return result

        return newfunc
