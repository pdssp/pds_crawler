# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
import logging
import os
from dataclasses import asdict
from dataclasses import dataclass
from json import dumps
from typing import Any
from typing import IO
from typing import Optional

from .load import Database
from .utils import Observer

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MessageModel:
    resource: str
    explanation: Any

    @classmethod
    def from_dict(cls, env):
        """Converts dictionary to MessageModel object.

        Args:
            env (dict): Dictionary containing resource and explanation fields.

        Returns:
            MessageModel: Object containing the fields.
        """
        return cls(**{k: v for k, v in env.items()})

    @property
    def __dict__(self):
        """Returns the dictionary representation of the object.

        Returns:
            dict: Dictionary representation of the object.
        """
        return asdict(self)

    @property
    def json(self):
        """Returns the json representation of the object.

        Returns:
            str: Json representation of the object.
        """
        return dumps(self.__dict__, indent=None)

    def __repr__(self) -> str:
        """Returns the printable representation of the object.

        Returns:
            str: Printable representation of the object.
        """
        return f"MessageModel({self.resource}, {self.explanation})"


class CrawlerReport(Observer):
    def __init__(self, db: Database):
        """Initializes the CrawlerReport object.

        Args:
            db (Database): Database object.
        """
        self.__db = db
        self.__name: str = "default_report"
        self.__file: Optional[IO] = None

    @property
    def name(self):
        """Returns the name of the report.

        Returns:
            str: The name of the report.
        """
        return self.__name

    @name.setter
    def name(self, value: str):
        """Sets the name of the report.

        Args:
            value (str): The name of the report.
        """
        self.__name = value

    def start_report(self, mode: str = "a"):
        """Starts the report and writes the header.

        Args:
            mode (str, optional): File opening mode. Defaults to "a".
        """
        self.__file = open(
            os.path.join(self.__db.base_directory, self.name), mode=mode
        )
        self._write_header()

    def _write_header(self):
        """Writes the header for the report."""
        header = """
        | Resource        |       Explanation |
        | ----------------|-------------------|
        """
        if self.__file is None:
            logger.error(header)
        else:
            self.__file.write(header)

    def close_report(self):
        """Closes the report file."""
        if self.__file is not None:
            self.__file.flush()
            self.__file.close()
            del self.__file
            self.__file = None

    def notify(self, observable, *args, **kwargs):
        """Receives the notification.

        Args:
            observable ([type]): Observable
        """
        message: MessageModel = args[0]
        if self.__file is None:
            logger.error(f"| {message.resource}  | {message.explanation} |")
        else:
            self.__file.write(
                f"| {message.resource}  | {message.explanation} |\n"
            )
