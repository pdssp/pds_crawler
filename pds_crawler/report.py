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
        return cls(**{k: v for k, v in env.items()})

    @property
    def __dict__(self):
        return asdict(self)

    @property
    def json(self):
        return dumps(self.__dict__, indent=None)

    def __repr__(self) -> str:
        return f"MessageModel({self.resource}, {self.explanation})"


class CrawlerReport(Observer):
    def __init__(self, db: Database):
        self.__db = db
        self.__name: str = "default_report"
        self.__file: Optional[IO] = None

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, value: str):
        self.__name = value

    def start_report(self, mode: str = "a"):
        self.__file = open(
            os.path.join(self.__db.base_directory, self.name), mode=mode
        )
        self._write_header()

    def _write_header(self):
        header = """
        | Resource        |       Explanation |
        | ----------------|-------------------|
        """
        if self.__file is None:
            logger.error(header)
        else:
            self.__file.write(header)

    def close_report(self):
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
