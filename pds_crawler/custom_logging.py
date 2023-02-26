# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""Module for customizing ths logs."""
import logging


class LogRecord(logging.LogRecord):  # pylint: disable=R0903
    """Specific class to handle output in logs."""

    def getMessage(self) -> str:
        """Returns the message.

        Format the message according to the type of the message.

        Returns:
            str: Returns the message
        """
        msg = self.msg
        if self.args:
            if isinstance(self.args, dict):
                msg = msg.format(**self.args)
            else:
                msg = msg.format(*self.args)
        return msg


class CustomColorFormatter(logging.Formatter):
    """Color formatter."""

    # Reset
    color_Off = "\033[0m"  # Text Reset

    log_colors = {
        logging.DEBUG: "\033[1;34m",  # blue
        logging.INFO: "\033[0;32m",  # green
        logging.WARNING: "\033[1;33m",  # yellow
        logging.ERROR: "\033[1;31m",  # red
        logging.CRITICAL: "\033[1;41m",  # red reverted
    }

    def format(self, record) -> str:
        """Format the log.

        Args:
            record: the log record

        Returns:
            str: the formatted log record
        """
        record.levelname = "{}{}{}".format(
            CustomColorFormatter.log_colors[record.levelno],
            record.levelname,
            CustomColorFormatter.color_Off,
        )
        record.msg = "{}{}{}".format(
            CustomColorFormatter.log_colors[record.levelno],
            record.msg,
            CustomColorFormatter.color_Off,
        )

        # Select the formatter according to the log if several handlers are
        # attached to the logger
        my_formatter = logging.Formatter
        my_handler = None
        handlers = logging.getLogger(__name__).handlers
        for handler in handlers:
            handler_level = handler.level
            if (
                handler_level
                == logging.getLogger(__name__).getEffectiveLevel()
            ):
                if handler.formatter:
                    my_formatter._fmt = (  # pylint: disable=W0212
                        handler.formatter._fmt  # pylint: disable=W0212
                    )
                my_handler = handler
                break
        if my_handler is not None:
            for handler in handlers:
                if handler != my_handler:
                    logging.getLogger(__name__).removeHandler(handler)
        return my_formatter.format(self, record)  # type: ignore


class ShellColorFormatter(CustomColorFormatter):
    """Shell Color formatter."""

    def format(self, record) -> str:
        """Format the log.

        Args:
            record: the log record

        Returns:
            str: the formatted log record
        """
        record.msg = "{}{}{}".format(
            CustomColorFormatter.log_colors[logging.INFO],
            record.msg,
            CustomColorFormatter.color_Off,
        )
        return record.msg
