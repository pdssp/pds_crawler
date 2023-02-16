# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Some Utilities."""
import logging
import os
import time
import tracemalloc
from functools import partial
from functools import wraps


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
                msg = f"Entering '{name}' (args={args}, kwargs={kwargs})"
                logger.log(level, msg)

            result = func(*args, **kwargs)

            if output and logger.getEffectiveLevel() >= level:
                msg = f"Exiting '{name}' (result={result})"
                logger.log(level, msg)

            return result

        return wrapped

    @staticmethod
    def time_spend(func=None, level=logging.DEBUG, threshold_in_ms=1000):
        """Monitor the performances of a function.

        Parameters
        ----------
        func: func
            Function to monitor (default: {None})
        level: int
            Level from which the monitoring starts (default: {logging.DEBUG})
        threshold_in_ms: int
            an alert is sent at any level when the function duration >
            threshold_in_ms (default: {1000})

        Returns
        -------
        object : the result of the function
        """
        if func is None:
            return partial(UtilsMonitoring.time_spend, level=level)

        @wraps(func)
        def newfunc(*args, **kwargs):
            name = func.__qualname__
            logger = logging.getLogger(__name__ + "." + name)
            start_time = time.time()
            result = func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.log(
                level,
                "function [{}] finished in {:.2f} ms".format(
                    func.__qualname__, elapsed_time * 1000
                ),
            )
            if float(elapsed_time) * 1000 > threshold_in_ms:
                logger.warning(
                    "function [{}] is too long to compute : {:.2f} ms".format(
                        func.__qualname__, elapsed_time * 1000
                    )
                )
            return result

        return newfunc

    @staticmethod
    def size(func=None, level=logging.INFO):
        """Monitor the number of records in a file.

        Parameters
        ----------
        func: func
            Function to monitor (default: {None})
        level: int
            Level from which the monitoring starts (default: {logging.INFO})

        Returns
        -------
        object : the result of the function
        """
        if func is None:
            return partial(UtilsMonitoring.size, level=level)

        @wraps(func)
        def newfunc(*args, **kwargs):
            name = func.__qualname__
            logger = logging.getLogger(__name__ + "." + name)
            filename = os.path.basename(args[1])
            logger.log(level, "Loading file '%s'", filename)
            result = func(*args, **kwargs)
            type_result = type(result)
            if type_result in [type({}), type([])]:
                nb_records = len(result)
            else:
                try:
                    nb_records = result.shape
                except AttributeError:  # noqa: W0703
                    nb_records = None

            if nb_records is not None:
                msg = (
                    f"File '{filename}' loaded with {str(nb_records)} records"
                )
                logger.info(msg)
            else:
                msg = f"Unable to load the number of records in file '{args[1]}' - type: {type_result}"  # pylint: disable=line-too-long
                logger.warning(msg)
            return result

        return newfunc

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
