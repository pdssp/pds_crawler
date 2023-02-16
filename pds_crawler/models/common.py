# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
from dataclasses import asdict
from dataclasses import dataclass
from json import dumps


@dataclass(frozen=True)
class AbstractModel:
    @classmethod
    def from_dict(cls, env):
        return cls(**{k: v for k, v in env.items()})

    @property
    def __dict__(self):
        return asdict(self)

    @property
    def json(self):
        return dumps(self.__dict__, indent=None)
