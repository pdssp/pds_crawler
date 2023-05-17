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
from typing import Iterable
from typing import List
from typing import Union
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
    """
    The UtilsMath class provides some utility functions for working with data types:

    - is_integer: determines whether a given value is an integer or not.
    - is_float: determines whether a given value is a float or not.
    - is_bool: determines whether a given value is a boolean or not.
    - convert_dt: attempts to convert a given string value to an appropriate data type (integer, float, boolean or string) if possible.
    """

    @staticmethod
    def is_integer(value: str) -> bool:
        """Determines whether the given value is an integer or not.
        Args:
            value (str): Value to check.
        Returns:
            bool: True if the value is an integer, False otherwise.
        """
        return isint(value)

    @staticmethod
    def is_float(value: str) -> bool:
        """Determines whether the given value is a float or not.
        Args:
            value (str): Value to check.
        Returns:
            bool: True if the value is a float, False otherwise.
        """
        return isfloat(value) and not isint(value)

    @staticmethod
    def is_bool(value: str) -> bool:
        """Determines whether the given value is a boolean or not.
        Args:
            value (str): Value to check.
        Returns:
            bool: True if the value is a boolean, False otherwise.
        """
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
        """Converts the given string value to the appropriate data type if possible.
        Args:
            value (str): Value to convert.
        Returns:
            Any: The converted value.
        """
        result: Any
        if not isinstance(value, str):
            result = value
        elif isint(value):
            result = int(value)
        elif isfloat(value):
            result = ffloat(value)
        elif UtilsMath.is_bool(value):
            result = value.lower() in ("yes", "true", "t")
        else:
            result = value
        return result


def cache_download(func):
    """Decorator to check if the download has been previously done and avoid redownloading.

    This decorator checks if a file has already been downloaded before calling the `parallel_requests` function.
    If the file has been downloaded previously, it is not downloaded again, and the cached file is used instead.
    If the file has not been downloaded, the function calls `parallel_requests` to download the file.

    Args:
        func (callable): The function to be decorated. It should be `parallel_requests`.

    Returns:
        callable: A decorated function.

    Raises:
        NotImplementedError: If the function being decorated is not `parallel_requests`.
    """

    @wraps(func)
    def cache_download_wrapper(*args, **kwargs):
        """Wrapper function that checks for cached downloads before downloading.

        This wrapper function checks if the URL of each file in the input `urls` list has been downloaded
        previously and skips the download if the file is found in the cache. If the file has not been
        downloaded, the function calls `parallel_requests` to download the file.

        Args:
            *args: Arguments passed to the decorated function.
            **kwargs: Keyword arguments passed to the decorated function.

        Returns:
            The result of the decorated function.

        Raises:
            NotImplementedError: If the function being decorated is not `parallel_requests`.
        """
        # Ensure that the function being wrapped is 'parallel_requests'
        if func.__name__ != "parallel_requests":
            raise NotImplementedError()

        # Get the directory and list of URLs to be downloaded
        directory: str = args[0]
        urls: List[str] = args[1]
        urls_copy: List[str] = urls.copy()

        # Check if each URL has already been downloaded and remove from urls_copy if so
        for url in urls:
            filepath: str = compute_downloaded_filepath(directory, url)
            if os.path.exists(filepath):
                logger.warning(f"file {filepath} in cache, skip the download")
                urls_copy.remove(url)
            else:
                logger.info(f"Downloading {url} in progress")

        # Call the original function with the new list of URLs
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
        session (Session, optional): http/https session. Defaults to None.

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
    """Downloads the contents of the given URL and saves it to a file.

    Args:
    - url (str): The URL to download.
    - filepath (str): The file path to save the downloaded contents.
    - timeout: The maximum number of seconds to wait for a response from the server.
    """
    # Send a GET request to the URL with the given timeout.
    response = requests.get(
        url, allow_redirects=True, verify=False, timeout=timeout
    )

    # If the response status code is 200 (OK), save the contents to a file.
    if response.status_code == 200:
        # Check if the response content type is HTML.
        if "text/html" in response.headers.get("content-type", ""):
            # If the content type is HTML, check if the response contains a "refresh" meta tag.
            soup = BeautifulSoup(response.content, "html.parser")
            redirect_elt = soup.find(
                "meta", attrs={"http-equiv": "refresh", "content": True}
            )
            if redirect_elt is not None:
                # If a "refresh" tag is found, extract the redirect URL and send another GET request to it.
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
        # Write the response content to the given file path.
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
    """Download files from a list of URLs using a ThreadPoolExecutor with a given number of workers.

    Args:
    - directory (str): the directory where to save the downloaded files
    - urls (List[str]): a list of URLs to download
    - nb_workers (int): the number of workers for the ThreadPoolExecutor
    - timeout (int): the maximum time to wait for a response from the server, in seconds
    - time_sleep (int): the time to sleep between two requests, in seconds
    - progress_bar (bool): whether to show a progress bar or not

    Raises:
    - requests.exceptions.ConnectionError: if a connection error occurs while downloading a file
    """

    def scrape(url):
        """Download a file from a URL.

        Args:
        - url (str): the URL to download

        Returns:
        - url (str): the URL that has been downloaded
        """
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
        ProgressLogger.write(
            f"{url} downloaded ({file_size_mb:0.03f} MB) in {int(hours):0>2}:{int(minutes):0>2}:{seconds:05.2f}",
            logger,
        )
        return url

    if len(urls) == 0:
        return

    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)

    progress_logger = ProgressLogger(
        total=len(urls),
        iterable=None,
        logger=logger,
        description="Downloading data",
        position=1,
        leave=False,
        disable_tqdm=not progress_bar,
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
            progress_logger.update(n=1)

    progress_logger.close()


def compute_downloaded_filepath(directory: str, url: str) -> str:
    """Computes the file path where a downloaded file will be saved based on the provided URL and directory.

    Args:
        directory (str): The directory where the downloaded file will be saved.
        url (str): The URL of the downloaded file.

    Returns:
        str: The file path where the downloaded file will be saved.
    """
    # Parse the URL to extract any query parameters
    parsed_url = urlparse(url)
    params: Dict[str, str] = parse_qs(parsed_url.query)  # type: ignore

    # Generate the filename based on the query parameters or the URL path
    filename: str
    if "ihid" in params:
        # If the URL contains "ihid" parameter, create a filename using "target", "ihid", "iid", "pt", and "offset" parameters
        filename = f"{params['target'][0]}_{params['ihid'][0]}_{params['iid'][0]}_{params['pt'][0]}_{params['offset'][0]}.json"
        filename = filename.replace(os.path.sep, "_")
    else:
        # If the URL doesn't contain "ihid" parameter, create a filename using the URL path
        path: str = parsed_url.path
        filename: str = os.path.basename(path).lower()

    # Return the full file path where the downloaded file will be saved
    return os.path.join(directory, filename)


def compute_download_directory_path(
    directory: str, target: str, ihid: str, iid: str, pt: str, ds: str
) -> str:
    """Computes the path where the file is downloaded based on a base directory and a metadata coming from the PDS.

    Args:
        directory (str): base direcory
        target (str): solar body
        ihid (str): plateform
        iid (str): instrument
        pt (str): product type
        ds (str): collection

    Returns:
        str: the path of the directory
    """
    # Create a list with the names of the five required folders/files
    items = [
        item.lower().replace(
            os.path.sep, "_"
        )  # Replace occurrences of os.path.sep with underscores in each name
        for item in [
            target,
            ihid,
            iid,
            pt,
            ds,
        ]  # For each required name, make a lowercase copy
    ]
    # Join all required names using os.path.sep as path separator and add the base path
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


class ProgressLogger:
    """A progress logger that can be used with or without tqdm."""

    def __init__(
        self,
        total: int,
        logger: logging.Logger,
        iterable: Union[Iterable, None] = None,
        description: str = "processing",
        disable_tqdm=False,
        *args,
        **kwargs,
    ):
        """A progress logger that can be used with or without tqdm.

        Args:
            total (int): The total number of items to be processed.
            logger (logging.Logger): The logger to use for progress updates.
            iterable (Union[Iterable, None]): The iterable to be processed.
            description (str): The description of the progress bar.
            disable_tqdm (bool): Whether to disable tqdm progress bar.
            *args: Additional positional arguments to be passed to tqdm.
            **kwargs: Additional keyword arguments to be passed to tqdm.

        Returns:
            None
        """
        self.total = total
        self.disable_tqdm = disable_tqdm
        self.description = description
        self.logger = logger
        self.iterable: Union[Iterable[str], None] = iterable
        self.nb: int = 0
        self.kwargs = kwargs
        if self.iterable is None:
            self.pbar = tqdm(
                total=total,
                desc=description,
                disable=self.disable_tqdm,
                **self.kwargs,
            )
            self._send_message()

    def _send_message(self):
        """Sends progress update messages to the logger at regular intervals."""
        if self.disable_tqdm and self.nb % 10 == 0:
            msg = f"{self.description} : {int(self.nb/self.total)}%"
            self.logger.info(msg)

    def __enter__(self):
        """Called when the 'with' statement is entered. Initializes the progress bar.

        Returns:
            self: The ProgressLogger instance.
        """
        self.pbar = tqdm(
            total=self.total,
            desc=self.description,
            disable=self.disable_tqdm,
            **self.kwargs,
        )
        self._send_message()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Called when the 'with' statement is exited. Closes the progress bar.

        Args:
            exc_type (type): The type of the exception, if one occurred.
            exc_value (Exception): The exception object, if one occurred.
            traceback (traceback): The traceback object, if one occurred.
        """
        if self.pbar:
            self.pbar.close()

    def __iter__(self):
        """Iterates over the iterable and updates the progress bar.

        Args:
            None

        Yields:
            i: The next item in the iterable.
        """
        if self.iterable and not self.disable_tqdm:
            for i in self.iterable:
                self.pbar.update(1)
                yield i
        elif self.iterable:
            for i in self.iterable:
                self.nb += 1
                self._send_message()
                yield i
        else:
            print("This is None !!!")
            yield None

    def update(self, n: int):
        """Updates the progress bar with the specified number of items.

        Args:
            n (int): The number of items to update.
        """
        if self.disable_tqdm:
            self.nb += 1
            self._send_message()
        else:
            self.pbar.update(n=n)

    def write_msg(self, msg: str):
        """Write a message using tqdm or the logger according if tqdm is used or not."""
        if self.disable_tqdm:
            logger.info(msg)
        else:
            tqdm.write(msg)

    @staticmethod
    def write(msg: str, logger: logging.Logger):
        """Write a message using the logger."""
        logger.info(msg)

    def close(self):
        """Close the tqdm progress bar."""
        if self.pbar:
            self.pbar.close()


class Locking:
    """Utility class for locking a file"""

    @staticmethod
    def lock_file(file):
        """Creates a lock file with the same name as the input file, but with ".lock" appended to the end.
        This method can be used to prevent other processes from accessing the same file simultaneously.

        Args:
            file (str): The name of the file to lock.

        Returns:
            None
        """
        # Create a lock file by appending ".lock" to the input file name
        lock_file = file + ".lock"

        # Initialize the locking flag to False
        locking = False

        # While the file is not locked, keep trying to create the lock file
        while not locking:
            try:
                # Try to create the lock file using the mkdir method
                os.mkdir(lock_file)

                # If successful, set the locking flag to True and exit the loop
                locking = True
            except OSError:
                # If the lock file already exists, wait for 0.1 seconds and try again
                time.sleep(0.1)

    @staticmethod
    def unlock_file(file: str):
        """Remove the lock file

        Args:
            file (str): The name of the file to unlock.
        """
        os.rmdir(file + ".lock")
