# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Module Name:
    pdssp_models

Description:
    Provides methods to make consistent the IDs and the used extensions in the PDSSP project.

Classes:
    PdsspModel
"""
import logging
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

from astropy.time import Time
from pymarsseason import Hemisphere
from pymarsseason import PyMarsSeason
from pymarsseason import Season

logger = logging.getLogger(__name__)


class PdsspModel:
    PREFIX_PDSSP: str = "urn:pdssp"

    @staticmethod
    def create_lab_id(lab: str) -> str:
        id = lab.replace("/", "_")  # STAC compatible
        return f"{PdsspModel.PREFIX_PDSSP}:{id.lower()}"

    @staticmethod
    def create_body_id(lab: str, solar_body_id: str) -> str:
        id = solar_body_id.replace("/", "_")  # STAC compatible
        return f"{PdsspModel.PREFIX_PDSSP}:{lab.lower()}:body:{id.lower()}"

    @staticmethod
    def create_mission_id(lab: str, mission_id: str) -> str:
        id = mission_id.replace("/", "_")  # STAC compatible
        return f"{PdsspModel.PREFIX_PDSSP}:{lab.lower()}:mission:{id.lower()}"

    @staticmethod
    def create_platform_id(lab: str, plateform_id: str) -> str:
        id = plateform_id.replace("/", "_")  # STAC compatible
        return (
            f"{PdsspModel.PREFIX_PDSSP}:{lab.lower()}:plateform:{id.lower()}"
        )

    @staticmethod
    def create_instru_id(lab: str, instrument_id: str) -> str:
        id = instrument_id.replace("/", "_")  # STAC compatible
        return f"{PdsspModel.PREFIX_PDSSP}:{lab.lower()}:instru:{id.lower()}"

    @staticmethod
    def create_collection_id(lab: str, collection_id: str) -> str:
        id = collection_id.replace("/", "_")  # STAC compatible
        return (
            f"{PdsspModel.PREFIX_PDSSP}:{lab.lower()}:collection:{id.lower()}"
        )

    @staticmethod
    def create_ssys_extension(body: str) -> Dict[str, Union[List, Dict]]:
        return {
            "stac_extensions": [
                "https://raw.githubusercontent.com/thareUSGS/ssys/main/json-schema/schema.json"
            ],
            "extra_fields": {"ssys:targets": [body]},
        }

    @staticmethod
    def add_mars_keywords_if_mars(
        body_id: str,
        ode_id: str,
        lat: Optional[float],
        slong: Optional[float],
        date: datetime,
    ) -> Dict[str, Any]:
        """Add specific keywords for Mars

        If Mars, add solar longitude and season otherwise
        returns an empty dictionary

        Args:
            body_id (str): solar body
            ode_id (str): ODE ID
            lat (Optional[float]): latitude of the footprint
            slong (Optional[float]): soalr longitude
            datetime (datetime): observation date

        Returns:
            Dict[str, Any]: _description_
        """
        mars: Dict[str, Any] = dict()
        if body_id.upper() != "MARS":
            return mars
        if lat is None:
            logger.warning(f"No latitude for Mars : {ode_id}")
            return mars
        py_mars_season: Dict[
            Hemisphere | str, Season | float
        ] = PyMarsSeason().compute_season_from_time(
            Time(date.isoformat(), format="isot", scale="utc")
        )
        if slong is None:
            mars["Solar_longitude"] = py_mars_season["ls"]

        hemisphere: Hemisphere = (
            Hemisphere.NORTH if float(lat) > 0 else Hemisphere.SOUTH
        )
        mars["season"] = hemisphere.value
        return mars
