# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""ODE services models

.. uml::

    class PdsRegistryModel {
        +ODEMetaDB: str
        +IHID: str
        +IHName: str
        +IID: str
        +IName: str
        +PT: str
        +PTName: str
        +DataSetId: str
        +NumberProducts: int
        +ValidTargets: Dict[str, List[str]]
        +MinOrbit: Optional[int]
        +MaxOrbit: Optional[int]
        +MinObservationTime: Optional[str]
        +MaxObservationTime: Optional[str]
        +NumberObservations: Optional[int]
        +SpecialValue1: Optional[str]
        +MinSpecialValue1: Optional[float]
        +MaxSpecialValue1: Optional[float]
        +SpecialValue2: Optional[str]
        +MinSpecialValue2: Optional[float]
        +MaxSpecialValue2: Optional[float]
    }

    class PdsRecordModel {
        +ode_id: str
        +pdsid: str
        +ihid: str
        +iid: str
        +pt: str
        +LabelFileName: str
        +Product_creation_time: str
        +Target_name: str
        +Data_Set_Id: str
        +Easternmost_longitude: float
        +Maximum_latitude: float
        +Minimum_latitude: float
        +Westernmost_longitude: float
        +Product_version_id: Optional[str]
        +RelativePathtoVol: Optional[str]
        +label: Optional[str]
        +PDS4LabelURL: Optional[str]
        +PDSVolume_Id: Optional[str]
        +Label_product_type: Optional[str]
        +Observation_id: Optional[str]
        +Observation_number: Optional[int]
        +Observation_type: Optional[str]
        +Producer_id: Optional[str]
        +Product_name: Optional[str]
        +Product_release_date: Optional[str]
        +Activity_id: Optional[str]
        +Predicted_dust_opacity: Optional[float]
        +Predicted_dust_opacity_text: Optional[str]
        +Observation_time: Optional[str]
        +SpaceCraft_clock_start_count: Optional[str]
        +SpaceCraft_clock_stop_count: Optional[str]
        +Start_orbit_number: Optional[int]
        +Stop_orbit_number: Optional[int]
        +UTC_start_time: Optional[str]
        +UTC_stop_time: Optional[str]
        +Emission_angle: Optional[float]
    }

    class ProductFile {
        +FileName: str
        +Type: Optional[str]
        +KBytes: Optional[float]
        +URL: Optional[str]
        +Description: Optional[str]
        +Creation_date: Optional[str]
    }

    PdsRecordModel --> ProductFile
"""
import inspect
import logging
import os
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from urllib.parse import urlparse

import numpy as np
import pystac
from astropy.time import Time
from pymarsseason import Hemisphere
from pymarsseason import PyMarsSeason
from pymarsseason import Season
from shapely import geometry
from shapely import wkt
from tqdm import tqdm

from ..exception import CrawlerError
from ..exception import DateConversionError
from ..exception import PdsCollectionAttributeError
from ..exception import PdsRecordAttributeError
from ..exception import PlanetNotFound
from ..utils import utc_to_iso
from ..utils import UtilsMath
from .common import AbstractModel

logger = logging.getLogger(__name__)


@dataclass(frozen=True, eq=True)
class ProductFile(AbstractModel):
    FileName: str
    Type: Optional[str] = field(default=None, repr=True, compare=True)
    KBytes: Optional[float] = field(default=None, repr=False, compare=False)
    URL: Optional[str] = field(default=None, repr=False, compare=False)
    Description: Optional[str] = field(default=None, repr=False, compare=False)
    Creation_date: Optional[str] = field(
        default=None, repr=False, compare=False
    )

    @classmethod
    def from_dict(cls, env):
        parameters = inspect.signature(cls).parameters
        return cls(
            **{
                k: UtilsMath.convert_dt(v)
                for k, v in env.items()
                if k in parameters
            }
        )


@dataclass(frozen=True, eq=True)
class PdsRegistryModel(AbstractModel):
    """ODE present products on an instrument host id, instrument id,
    and product type structure.

    see : https://oderest.rsl.wustl.edu/ODE_REST_V2.1.pdf
    """

    ODEMetaDB: str
    """ODE Meta DB – can be used as a Target input"""
    IHID: str
    """Instrument Host Id"""
    IHName: str = field(repr=False, compare=False)
    """Instrument Host Name"""
    IID: str
    """Instrument Id"""
    IName: str = field(repr=False, compare=False)
    """Instrument Name"""
    PT: str
    """Product Type"""
    PTName: str = field(repr=False, compare=False)
    """Product Type Name"""
    DataSetId: str
    """Data Set Id"""
    NumberProducts: int
    """Number of products with this instrument host/instrument/product type"""
    ValidTargets: Dict[str, List[str]] = field(repr=False, compare=False)
    """Set of valid target values for the Target query parameter for a given
    instrument host, instrument, product type. IIPTs are usually
    targeted to the primary body for that ODE meta database. Example,
    the products in the ODE Mars meta database primarily target Mars.
    But some IIPTs have additional targets such as DIEMOS,
    PHOBOS, or special calibration targets. These targets can then be
    used in the query parameter TARGET=."""
    MinOrbit: Optional[int] = field(default=None, repr=False, compare=False)
    """Minimum orbit value for all products with this instrument
    host/instrument/product type"""
    MaxOrbit: Optional[int] = field(default=None, repr=False, compare=False)
    """Maximum orbit value for all products with this instrument
    host/instrument/product type"""
    MinObservationTime: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Minimum observation time value for all products with this
    instrument host/instrument/product type"""
    MaxObservationTime: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Maximum observation time value for all products with this
    instrument host/instrument/product type"""
    NumberObservations: Optional[int] = field(
        default=None, repr=False, compare=False
    )
    """Number of observation values found in the products (valid only for
    selected instrument host/instrument/product types such as LOLA)"""
    SpecialValue1: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Some sets have special values unique to that set. This is the name
    or description of that value. Special values capture product type
    specific information. For example, LRO LOLA RDRs include a
    special value that holds the range of altimetry data. """
    MinSpecialValue1: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Minimum special value 1"""
    MaxSpecialValue1: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Maximum special value 1"""
    SpecialValue2: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Some sets have a second special values unique to that set. This is
    the name or description of that value."""
    MinSpecialValue2: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Minimum special value 2"""
    MaxSpecialValue2: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Maximum special value 2"""

    def get_collection_id(self) -> str:
        return f"urn:pdssp:pds:collection:{self.get_collection()}"

    def get_collection(self) -> str:
        return self.DataSetId

    def get_instrument_id(self) -> str:
        return f"urn:pdssp:pds:instru:{self.IID}"

    def get_instrument(self) -> str:
        return self.IName

    def get_plateform_id(self) -> str:
        return f"urn:pdssp:pds:plateform:{self.IHID}"

    def get_plateform(self) -> str:
        return self.IHName

    def get_mission_id(self) -> str:
        return f"urn:pdssp:pds:mission:{self.IHID}"

    def get_mission(self) -> str:
        return self.IHName

    def get_planet(self) -> str:
        planet: str = self.ODEMetaDB[0].upper() + self.ODEMetaDB[1:].lower()
        return planet

    def get_planet_id(self) -> str:
        return f"urn:pdssp:pds:planet:{self.get_planet()}"

    def get_range_orbit(self) -> Optional[pystac.RangeSummary]:
        range: Optional[pystac.RangeSummary] = None
        if self.MinOrbit is not None and self.MaxOrbit is not None:
            range = pystac.RangeSummary(
                minimum=int(self.MinOrbit), maximum=int(self.MaxOrbit)  # type: ignore
            )
        return range

    def get_range_special_value1(self) -> Optional[pystac.RangeSummary]:
        range: Optional[pystac.RangeSummary] = None
        if (
            self.MinSpecialValue1 is not None
            and self.MaxSpecialValue1 is not None
        ):
            range = pystac.RangeSummary(
                minimum=float(self.MinSpecialValue1),  # type: ignore
                maximum=float(self.MaxSpecialValue1),  # type: ignore
            )
        return range

    def get_range_special_value2(self) -> Optional[pystac.RangeSummary]:
        range: Optional[pystac.RangeSummary] = None
        if (
            self.MinSpecialValue2 is not None
            and self.MaxSpecialValue2 is not None
        ):
            range = pystac.RangeSummary(
                minimum=self.MinSpecialValue2, maximum=self.MaxSpecialValue2  # type: ignore
            )
        return range

    def get_range_time(self) -> Optional[pystac.RangeSummary]:
        range: Optional[pystac.RangeSummary] = None
        if (
            self.MinObservationTime is not None
            and self.MaxObservationTime is not None
        ):
            range = pystac.RangeSummary(
                minimum=self.MinObservationTime,  # type: ignore
                maximum=self.MaxObservationTime,  # type: ignore
            )
        return range

    def get_summaries(self) -> Optional[pystac.Summaries]:
        summaries: Dict[str, Any] = dict()
        range_orbits = self.get_range_orbit()
        range_special_value1 = self.get_range_special_value1()
        range_special_value2 = self.get_range_special_value2()
        range_time = self.get_range_time()
        if range_orbits is not None:
            summaries["orbit"] = range_orbits
        if range_special_value1 is not None:
            summaries[self.SpecialValue1] = range_special_value1  # type: ignore
        if range_special_value2 is not None:
            summaries[self.SpecialValue2] = range_special_value2  # type: ignore
        if range_time is not None:
            summaries["observation_time"] = range_time
        result: Optional[pystac.Summaries]
        if len(summaries) > 0:
            result = pystac.Summaries(summaries=summaries)
        else:
            result = None
        return result

    @classmethod
    def from_dict(cls, env):
        collection_id = (
            f'{env["ODEMetaDB"]}_{env["IHID"]}_{env["IID"]}_{env["DataSetId"]}'
        )
        try:
            if "ValidFootprints" in env and env["ValidFootprints"] == "F":
                logger.warning(
                    f"Missing `Footprints` for {collection_id} IIPTSet: not added, return None."
                )
                return None

            if "NumberProducts" in env and int(env["NumberProducts"]) == 0:
                logger.warning(
                    f"Missing `NumberProducts` for {collection_id} IIPTSet: not added, return None."
                )
                return None

            parameters = inspect.signature(cls).parameters
            return cls(
                **{
                    k: UtilsMath.convert_dt(v)
                    for k, v in env.items()
                    if k in parameters
                }
            )
        except KeyError as err:
            raise PdsCollectionAttributeError(
                f"[KeyError] - {err} is missing for {collection_id}"
            )
        except TypeError as err:
            raise PdsCollectionAttributeError(
                f"[TypeError] - {err} is missing for {collection_id}"
            )

    def create_stac_collection(self) -> pystac.Collection:
        collection = pystac.Collection(
            id=self.get_collection_id(),
            description=f"{self.PTName} products",
            extent=pystac.Extent(
                pystac.SpatialExtent(bboxes=[[]]),
                pystac.TemporalExtent(intervals=[[None, None]]),
            ),
            title=self.get_collection(),
            extra_fields={
                "instruments": [self.get_instrument()],
                "plateform": self.get_plateform(),
                "mission": self.get_mission(),
            },
            license="CC0-1.0",
        )
        summaries = self.get_summaries()
        if summaries is not None:
            collection.summaries = summaries
        return collection

    def create_stac_instru_catalog(self) -> pystac.Catalog:
        return pystac.Catalog(
            id=self.get_instrument_id(),
            title=self.get_instrument(),
            description="",
        )

    def create_stac_platform_catalog(self) -> pystac.Catalog:
        return pystac.Catalog(
            id=self.get_plateform_id(),
            title=self.get_plateform(),
            description="",
        )

    def create_stac_mission_catalog(self) -> pystac.Catalog:
        return pystac.Catalog(
            id=self.get_mission_id(), title=self.get_mission(), description=""
        )

    def create_stac_planet_catalog(self) -> pystac.Catalog:
        url: Optional[str] = None
        match self.ODEMetaDB.upper():
            case "VENUS":
                url = "https://solarsystem.nasa.gov/rails/active_storage/blobs/eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaHBBcTBFIiwiZXhwIjpudWxsLCJwdXIiOiJibG9iX2lkIn19--1d5cefd65606b80f88a16ac6c3e4afde8d2e1ee6/PIA00271_detail.jpg?disposition=attachment"
            case "MERCURY":
                url = "https://www.nasa.gov/sites/default/files/mercury_1.jpg"
            case "MARS":
                url = "https://mars.nasa.gov/system/site_config_values/meta_share_images/1_mars-nasa-gov.jpg"
            case "MOON":
                url = "https://www.nasa.gov/sites/default/files/styles/full_width_feature/public/thumbnails/image/opo9914d.jpg"
            case _:
                raise PlanetNotFound(
                    f"Unexpected planet to parse : {self.ODEMetaDB.upper()}"
                )
        catalog = pystac.Catalog(
            id=self.get_planet_id(),
            title=self.get_planet(),
            description="",
            stac_extensions=[
                "https://raw.githubusercontent.com/thareUSGS/ssys/main/json-schema/schema.json"
            ],
            extra_fields={"ssys:targets": [self.get_planet()]},
        )
        catalog.add_link(
            pystac.Link(
                rel=pystac.RelType.PREVIEW,
                target=url,
                media_type=pystac.MediaType.JPEG,
                title=self.ODEMetaDB,
                extra_fields={"credits": "NASA"},
            )
        )
        return catalog

    def to_hdf5(self, store_db: Any):
        """Saves the information in the attributes of a HDF5 node

        Args:
            store_db (Any): HDF5 node
        """
        pds_collection_dict = self.__dict__
        for key in pds_collection_dict.keys():
            value = pds_collection_dict[key]
            # when type is a dictionnary or list, a specific datatype
            # is needed to encode an attribute in HDF5
            if isinstance(value, dict) or isinstance(value, list):
                store_db.attrs[key] = np.string_(str(value))  # type: ignore
            elif value is not None:
                store_db.attrs[key] = value


@dataclass(frozen=True, eq=True)
class PdsRecordModel(AbstractModel):
    """ODE meta-data."""

    ode_id: str = field(repr=False, compare=False)
    """An internal ODE product identifier.
    NOTE: This id is assigned by ODE when the product is
    added to the ODE metadata database. It is
    generally stable but can be changed when the
    ODE metadatabase is rebuilt. In general, this id
    should only be used shortly after acquisition."""
    pdsid: str = field(repr=False, compare=False)
    """PDS Product Id"""
    ihid: str
    """Instrument host id. See ODE for valid instrument host ids"""
    iid: str
    """Instrument id. See ODE for valid instrument ids"""
    pt: str
    """ODE Product type. This is ODE's product type.
    In general, it is obtained from the label but can
    be changed or depending on whether a label has
    a product type, whether there are other products
    in the same instrument with the same product
    type in the label, etc. If this is not the same
    product type as in the label, the return will
    include a Label_Product_Type value as well"""
    LabelFileName: str = field(repr=False, compare=False)
    """The file name of the product label"""
    Product_creation_time: str = field(repr=False, compare=False)
    """Product creation time (UTC)"""
    Target_name: str
    """Product target (example: Mars)"""
    Data_Set_Id: str = field(repr=True, compare=True)
    """PDS Data Set Id"""
    Easternmost_longitude: float = field(repr=False, compare=False)
    """Longitude 0-360 Easternmost longitude of the footprint"""
    Maximum_latitude: float = field(repr=False, compare=False)
    """Planetocentric maximum latitude of the footprint"""
    Minimum_latitude: float = field(repr=False, compare=False)
    """Planetocentric minimum latitude of the footprint"""
    Westernmost_longitude: float = field(repr=False, compare=False)
    """Longitude 0-360 Westernmost longitude of the footprint"""
    Product_version_id: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Product version"""
    RelativePathtoVol: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """The relative path from the volume root to the
    product label file"""
    label: Optional[str] = field(default=None, repr=False, compare=False)
    """Complete product label for PDS3 product labels"""
    PDS4LabelURL: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Pointer to PDS4 XML label for PDS4 products"""
    PDSVolume_Id: Optional[str] = field(default=None)
    """Volume Id"""
    Label_product_type: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Label product type (if it exists in the label and is
    different from the ODE_Product_Type)"""
    Observation_id: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Identifies a scientific observation within a dataset."""
    Observation_number: Optional[int] = field(
        default=None, repr=False, compare=False
    )
    """Monotonically increasing ordinal counter of the
    EDRs generated for a particular OBSERVATION_ID. """
    Observation_type: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Identifies the general type of an observation"""
    Producer_id: Optional[str] = field(default=None, repr=False, compare=False)
    """Producer id"""
    Product_name: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Product name"""
    Product_release_date: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Product release date"""
    Activity_id: Optional[str] = field(default=None, repr=False, compare=False)
    """Label Activity id"""
    Predicted_dust_opacity: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Predicted dust opacity"""
    Predicted_dust_opacity_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Predicted dust opacity text."""
    Observation_time: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Observation time (mid-point between the start
    and end of the observation)"""
    SpaceCraft_clock_start_count: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Spacecraft clock start"""
    SpaceCraft_clock_stop_count: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Spacecraft clock end"""
    Start_orbit_number: Optional[int] = field(
        default=None, repr=False, compare=False
    )
    """Start orbit number"""
    Stop_orbit_number: Optional[int] = field(
        default=None, repr=False, compare=False
    )
    """End orbit number"""
    UTC_start_time: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Observation start time in UTC"""
    UTC_stop_time: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Observation end time in UTC"""
    Emission_angle: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Emission angle"""
    Emission_angle_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Emission angle text from the product label"""
    Phase_angle: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Phase angle"""
    Phase_angle_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Phase angle text from the product label"""
    Incidence_angle: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Incidence angle"""
    Incidence_angle_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Incidence angle text from the product label"""
    Map_resolution: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Map resolution"""
    Map_resolution_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Map resolution text from the product label"""
    Map_scale: Optional[float] = field(default=None, repr=False, compare=False)
    """Map scale"""
    Map_scale_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Map scale text from the product label"""
    Solar_distance: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Solar distance"""
    Solar_distance_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Solar distance text from the product label"""
    Solar_longitude: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Solar longitude"""
    Center_georeferenced: Optional[bool] = field(
        default=None, repr=False, compare=False
    )
    """T if the product has a footprint center"""
    Center_latitude: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Planetocentric footprint center latitude"""
    Center_longitude: Optional[float] = field(
        default=None, repr=False, compare=False
    )
    """Longitude 0-360 center longitude"""
    Center_latitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Text found in the center latitude label keyword
    if the center latitude is not a valid number"""
    Center_longitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Text found in the center longitude label keyword
    if the center longitude is not a valid number"""
    BB_georeferenced: Optional[bool] = field(
        default=None, repr=False, compare=False
    )
    """T if the product has a footprint bounding box"""
    Easternmost_longitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Longitude 0-360 Easternmost longitude of the footprint"""
    Maximum_latitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Planetocentric maximum latitude of the footprint"""
    Minimum_latitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Planetocentric minimum latitude of the footprint"""
    Westernmost_longitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Longitude 0-360 Westernmost longitude of the footprint"""
    Easternmost_longitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Text found in the easternmost longitude label
    keyword if the easternmost longitude is not a
    valid number"""
    Maximum_latitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Text found in the maximum latitude label
    keyword if the maximum latitude is not a valid
    number"""
    Minimum_latitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Text found in the minimum latitude label
    keyword if the minimum latitude is not a valid
    number"""
    Westernmost_longitude_text: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Text found in the westernmost longitude label
    keyword if the westernmost longitude is not a
    valid number"""
    Footprint_geometry: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Cylindrical projected planetocentric, longitude
    0-360 product footprint in WKT format. Only if
    there is a valid footprint. Note - this is a
    cylindrical projected footprint. The footprint has
    been split into multiple polygons when crossing
    the 0/360 longitude line and any footprints that
    cross the poles have been adjusted to add points
    to and around the pole. It is meant for use in
    cylindrical projects and is not appropriate for
    spherical displays."""
    Footprint_C0_geometry: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Planetocentric, longitude -180-180 product
    footprint in WKT format. Only if there is a valid
    footprint. Note - this is a cylindrical projected
    footprint. The footprint has been split into
    multiple polygons when crossing the -180/180
    longitude line and any footprints that cross the
    poles have been adjusted to add points to and
    around the pole. It is meant for use in cylindrical
    projects and is not appropriate for spherical
    displays."""
    Footprint_GL_geometry: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Planetocentric, longitude 0-360 product
    footprint in WKT format. Only if there is a valid
    footprint. This is not a projected footprint."""
    Footprint_NP_geometry: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Stereographic south polar projected footprint in
    WKT format. Only if there is a valid footprint.
    This footprint has been projected into meters in
    stereographic north polar projection"""
    Footprint_SP_geometry: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """Stereographic south polar projected footprint in
    WKT format. Only if there is a valid footprint.
    This footprint has been projected into meters in
    stereographic south polar projection."""
    Footprints_cross_meridian: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """T if the footprint crosses the 0/360 longitude line"""
    Pole_state: Optional[str] = field(default=None, repr=False, compare=False)
    """String of "none", "north", or "south"""
    Footprint_souce: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """A brief description of where the footprint came from"""
    USGS_Sites: Optional[str] = field(default=None, repr=False, compare=False)
    """A USGS site that this product's footprint partially or completely covers"""
    Comment: Optional[str] = field(default=None, repr=False, compare=False)
    """Any associated comment"""
    Description: Optional[str] = field(default=None, repr=False, compare=False)
    """Label description"""
    ODE_notes: Optional[str] = field(default=None, repr=False, compare=False)
    """A note about how data has been entered into ODE"""
    External_url: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """URL to an external reference to the product.
    Product type specific but usually something like
    the HiRISE site."""
    External_url2: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """URL to an external reference to the product.
    Product type specific but usually something like
    the HiRISE site."""
    External_url3: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    """URL to an external reference to the product.
    Product type specific but usually something like
    the HiRISE site"""
    FilesURL: Optional[str] = field(default=None, repr=False, compare=False)
    ProductURL: Optional[str] = field(default=None, repr=False, compare=False)
    LabelURL: Optional[str] = field(default=None, repr=False, compare=False)
    Product_files: Optional[List[ProductFile]] = field(
        default=None, repr=False, compare=False
    )
    browse: Optional[str] = field(default=None, repr=False, compare=False)
    """If there is an ODE browse image - returns a base64 string of the PNG image"""
    thumbnail: Optional[str] = field(default=None, repr=False, compare=False)
    """If there is an ODE thumbnail image - returns a base64 string of the PNG image"""

    def get_id(self):
        return str(self.ode_id)

    def get_title(self):
        return self.pdsid

    def get_description(self):
        return self.Description

    def get_collection_id(self) -> str:
        return f"urn:pdssp:pds:collection:{self.get_collection()}"

    def get_collection(self) -> str:
        return self.Data_Set_Id

    def get_instrument_id(self) -> str:
        return f"urn:pdssp:pds:instru:{self.iid}"

    def get_instrument(self, pds_registry_model: PdsRegistryModel) -> str:
        return pds_registry_model.IName

    def get_plateform_id(self) -> str:
        return f"urn:pdssp:pds:plateform:{self.ihid}"

    def get_plateform(self, pds_registry_model: PdsRegistryModel) -> str:
        return pds_registry_model.IHName

    def get_mission_id(self) -> str:
        return f"urn:pdssp:pds:mission:{self.get_mission()}"

    def get_mission(self) -> str:
        return self.ihid

    def get_planet(self) -> str:
        planet: str = (
            self.Target_name[0].upper() + self.Target_name[1:].lower()
        )
        return planet

    def get_planet_id(self) -> str:
        return f"urn:pdssp:pds:planet:{self.get_planet()}"

    def get_start_date(self):
        start_date: Optional[datetime] = None
        if self.UTC_start_time is not None:
            try:
                start_date = datetime.fromisoformat(
                    utc_to_iso(self.UTC_start_time)
                )
            except:  # noqa: E722
                start_date = None
        return start_date

    def get_stop_date(self):
        stop_date: Optional[datetime] = None
        if self.UTC_stop_time is not None:
            try:
                stop_date = datetime.fromisoformat(
                    utc_to_iso(self.UTC_stop_time)
                )
            except:  # noqa: E722
                stop_date = None
        return stop_date

    def get_geometry(self) -> Dict[str, Any]:
        return geometry.mapping(wkt.loads(self.Footprint_C0_geometry))

    def get_bbox(self) -> list[float]:
        return [
            self.Westernmost_longitude,
            self.Minimum_latitude,
            self.Easternmost_longitude,
            self.Maximum_latitude,
        ]

    def get_gsd(self) -> Optional[float]:
        result: Optional[float] = None
        if self.Map_resolution is not None:
            result = self.Map_resolution
        return result

    def get_datetime(self) -> datetime:
        date_obs: str
        if self.Observation_time and not self.Observation_time.startswith(
            "0000"
        ):
            date_obs = self.Observation_time
        elif (
            self.Product_creation_time
            and not self.Product_creation_time.startswith("0000")
        ):
            date_obs = self.Product_creation_time
            logger.warning(
                f"Cannot find {self.Observation_time}, use Product_creation_time as datetime for {self}"
            )
        elif self.Product_release_date:
            date_obs = self.Product_release_date
            logger.warning(
                f"Cannot find {self.Observation_time}, use Product_creation_time as datetime for {self}"
            )
        else:
            raise ValueError("No datetime")
        return datetime.fromisoformat(utc_to_iso(date_obs))

    def add_mars_keywords_if_mars(self) -> Dict[str, Any]:
        """Add specific keywords for Mars

        If Mars, add solar longitude and season otherwise
        returns an empty dictionary

        Raises:
            ValueError: _description_

        Returns:
            Dict[str, Any]: _description_
        """
        mars: Dict[str, Any] = dict()
        if self.get_planet() != "Mars":
            return mars
        if self.Center_latitude is None:
            logger.warning(f"No latitude for Mars : {self.ode_id}")
            return mars
        py_mars_season: Dict[
            Hemisphere | str, Season | float
        ] = PyMarsSeason().compute_season_from_time(
            Time(self.get_datetime().isoformat(), format="isot", scale="utc")
        )
        if self.Solar_longitude is None:
            mars["Solar_longitude"] = py_mars_season["ls"]

        hemisphere: Hemisphere = (
            Hemisphere.NORTH
            if float(self.Center_latitude) > 0
            else Hemisphere.SOUTH
        )
        mars["season"] = hemisphere.value
        return mars

    def get_properties(self) -> Dict[str, Any]:
        properties = {
            key: self.__dict__[key]
            for key in self.__dict__.keys()
            if key
            in [
                "pt",
                "LabelFileName",
                "Product_creation_time",
                "Product_version_id",
                "label",
                "PDS4LabelURL",
                "Data_Set_Id",
                "PDSVolume_Id",
                "Label_product_type",
                "Observation_id",
                "Observation_number",
                "Observation_type",
                "Producer_id",
                "Product_name",
                "Product_release_date",
                "Activity_id",
                "Predicted_dust_opacity",
                "Predicted_dust_opacity_text",
                "Observation_time",
                "SpaceCraft_clock_start_count",
                "SpaceCraft_clock_stop_count",
                "Start_orbit_number",
                "Stop_orbit_number",
                "UTC_start_time",
                "UTC_stop_time",
                "Emission_angle",
                "Emission_angle_text",
                "Phase_angle",
                "Phase_angle_text",
                "Incidence_angle",
                "Incidence_angle_text",
                "Map_resolution_text",
                "Map_scale",
                "Map_scale_text",
                "Solar_distance",
                "Solar_distance_text",
                "Solar_longitude",
                "Center_latitude",
                "Center_longitude",
                "Center_latitude_text",
                "USGS_Sites",
                "Comment",
            ]
            and self.__dict__[key] is not None
        }
        properties.update(self.add_mars_keywords_if_mars())
        return properties

    def set_common_metadata(
        self, item: pystac.Item, pds_registry: PdsRegistryModel
    ):
        item.common_metadata.license = "CC0-1.0"
        item.common_metadata.instruments = [self.get_instrument(pds_registry)]
        item.common_metadata.platform = self.get_plateform(pds_registry)
        item.common_metadata.mission = self.get_mission()
        item.common_metadata.description = self.get_description()
        start_date = self.get_start_date()
        stop_date = self.get_stop_date()
        if start_date is not None:
            item.common_metadata.start_datetime = start_date
        if stop_date is not None:
            item.common_metadata.end_datetime = stop_date
        gsd = self.get_gsd()
        if gsd is not None:
            item.common_metadata.gsd = gsd

    def add_assets_product_types(self, item: pystac.Item):
        if not self.Product_files:
            return

        for product_file in self.Product_files:
            if not product_file.URL:
                continue
            item.add_asset(
                product_file.FileName,
                pystac.Asset(
                    href=product_file.URL,
                    title=product_file.FileName,
                    description=product_file.Description,
                    roles=["metadata"],
                ),
            )

    def add_assets_browse(self, item: pystac.Item):
        if self.browse is not None:
            parsed_url = urlparse(self.browse)
            path: str = parsed_url.path
            filename: str = os.path.basename(path)
            item.add_asset(
                filename,
                pystac.Asset(
                    href=self.browse,
                    title=filename,
                    description="Browse image",
                    roles=["overview"],
                ),
            )

    def add_assets_thumbnail(self, item: pystac.Item):
        if self.thumbnail is not None:
            parsed_url = urlparse(self.thumbnail)
            path: str = parsed_url.path
            filename: str = os.path.basename(path)
            item.add_asset(
                filename,
                pystac.Asset(
                    href=self.thumbnail,
                    title=filename,
                    description="Thumbnail image",
                    roles=["thumbnail"],
                ),
            )

    def add_assets_data(self, item: pystac.Item):
        if self.LabelURL is not None:
            parsed_url = urlparse(self.LabelURL)
            path: str = parsed_url.path
            filename: str = os.path.basename(path)
            item.add_asset(
                filename,
                pystac.Asset(
                    href=self.LabelURL,
                    title=filename,
                    description="Browse Label",
                    roles=["metadata"],
                ),
            )

        if self.ProductURL is not None:
            parsed_url = urlparse(self.ProductURL)
            path: str = parsed_url.path
            filename: str = os.path.basename(path)
            item.add_asset(
                filename,
                pystac.Asset(
                    href=self.ProductURL,
                    title=filename,
                    description="Product URL",
                    roles=["data"],
                ),
            )

        if self.FilesURL is not None:
            parsed_url = urlparse(self.FilesURL)
            path: str = parsed_url.path
            filename: str = os.path.basename(path)
            item.add_asset(
                filename,
                pystac.Asset(
                    href=self.FilesURL,
                    title=filename,
                    description="Files URL",
                    roles=["metadata"],
                ),
            )

    def add_assets_external_files(self, item: pystac.Item):
        if self.External_url is not None:
            parsed_url = urlparse(self.External_url)
            path: str = parsed_url.path
            filename: str = os.path.basename(path)
            item.add_asset(
                filename,
                pystac.Asset(
                    href=self.External_url,
                    title=filename,
                    description="External URL",
                    roles=["metadata"],
                ),
            )

        if self.External_url2 is not None:
            parsed_url = urlparse(self.External_url2)
            path: str = parsed_url.path
            filename: str = os.path.basename(path)
            item.add_asset(
                filename,
                pystac.Asset(
                    href=self.External_url2,
                    title=filename,
                    description="External URL2",
                    roles=["metadata"],
                ),
            )

        if self.External_url3 is not None:
            parsed_url = urlparse(self.External_url3)
            path: str = parsed_url.path
            filename: str = os.path.basename(path)
            item.add_asset(
                filename,
                pystac.Asset(
                    href=self.External_url3,
                    title=filename,
                    description="External URL3",
                    roles=["metadata"],
                ),
            )

    def add_ssys_extention(self, item: pystac.Item):
        item.stac_extensions = [
            "https://raw.githubusercontent.com/thareUSGS/ssys/main/json-schema/schema.json"
        ]
        if item.properties is None:
            item.properties = {"ssys:targets": [self.Target_name]}
        else:
            item.properties["ssys:targets"] = [self.Target_name]

    @classmethod
    def from_dict(cls, env):
        try:
            if "Footprint_geometry" not in env:
                # logger.warning(f'Missing data = records.get_sample_records_pds(col.ODEMetaDB,col.IHID,col.IID,col.PT, col.NumberProducts, limit=1)`Footprint_geometry` for IIPTSet: not added, return None.')
                return None
            parameters = inspect.signature(cls).parameters
            data = env.copy()
            if "Product_files" in data:
                data["Product_files"] = [
                    ProductFile.from_dict(item)
                    for item in data["Product_files"]["Product_file"]
                ]
            return cls(
                **{
                    k: UtilsMath.convert_dt(v)
                    for k, v in data.items()
                    if k in parameters
                }
            )
        except KeyError as err:
            logger.error(env)
            collection_id = f'{env["Target_name"]}_{env["ihid"]}_{env["iid"]}'
            if "Data_Set_Id" in env:
                collection_id = f"{collection_id}_{env['Data_Set_Id']}"
            raise PdsRecordAttributeError(
                f"[KeyError] - {err} is missing for {collection_id}"
            )
        except TypeError as err:
            logger.error(env)
            collection_id = f'{env["Target_name"]}_{env["ihid"]}_{env["iid"]}'
            if "Data_Set_Id" in env:
                collection_id = f"{collection_id}_{env['Data_Set_Id']}"
            raise PdsRecordAttributeError(
                f"[TypeError] - {err} is missing for {collection_id}"
            )

    def to_stac_item(self, pds_registry: PdsRegistryModel) -> pystac.Item:
        try:
            item = pystac.Item(
                id=self.get_id(),
                geometry=self.get_geometry(),
                bbox=self.get_bbox(),
                datetime=self.get_datetime(),
                properties=self.get_properties(),
                collection=self.get_collection_id(),
            )
            self.set_common_metadata(item, pds_registry)
            self.add_assets_product_types(item)
            self.add_assets_browse(item)
            self.add_assets_thumbnail(item)
            self.add_assets_data(item)
            self.add_assets_external_files(item)
            self.add_ssys_extention(item)

            return item
        except PdsCollectionAttributeError as err:
            raise CrawlerError(
                f"""
            error : {err.__class__.__name__}
            Message : {err.__cause__}
            class: {self}
            data: {self.__dict__}
            """
            )
        except PdsRecordAttributeError as err:
            raise CrawlerError(
                f"""
            error : {err.__class__.__name__}
            Message : {err.__cause__}
            class: {self}
            data: {self.__dict__}
            """
            )
        except PlanetNotFound as err:
            raise CrawlerError(
                f"""
            error : {err.__class__.__name__}
            Message : {err.__cause__}
            class: {self}
            data: {self.__dict__}
            """
            )
        except DateConversionError as err:
            raise CrawlerError(
                f"""
            error : {err.__class__.__name__}
            Message : {err.__cause__}
            class: {self}
            data: {self.__dict__}
            """
            )
        except Exception as err:
            logger.exception(f"Unexpected error : {err}")
            raise CrawlerError(
                f"""
            Unexpected error : {err.__cause__}
            class: {self}
            data: {self.__dict__}
            """
            )


@dataclass(frozen=True, eq=True)
class PdsRecordsModel(AbstractModel):
    pds_records_model: List[PdsRecordModel]
    target_name: str
    plateform_id: str
    instrument_id: str
    dataset_id: str

    @classmethod
    def from_dict(cls, env) -> Optional["PdsRecordsModel"]:
        result: Optional[PdsRecordsModel]
        pds_records_model = list()
        for item in env:
            pds_record_model: PdsRecordModel = PdsRecordModel.from_dict(item)
            if pds_record_model is not None:
                pds_records_model.append(pds_record_model)
        if len(pds_records_model) == 0:
            result = None
        else:
            result = PdsRecordsModel(
                pds_records_model=pds_records_model,
                target_name=pds_records_model[0].Target_name,
                plateform_id=pds_records_model[0].ihid,
                instrument_id=pds_records_model[0].iid,
                dataset_id=pds_records_model[0].Data_Set_Id,
            )
        return result

    def to_stac_item_iter(
        self, pds_registry: PdsRegistryModel, progress_bar: bool = True
    ) -> Iterator[pystac.Item]:
        for pds_record_model in tqdm(
            self.pds_records_model,
            desc="pystac.Item processing",
            total=len(self.pds_records_model),
            position=2,
            leave=False,
            disable=not progress_bar,
        ):
            yield pds_record_model.to_stac_item(pds_registry)

    def __repr__(self) -> str:
        return f"PdsRecordsModel({self.target_name}/{self.plateform_id}/{self.instrument_id}/{self.dataset_id}, nb_records={len(self.pds_records_model)})"
