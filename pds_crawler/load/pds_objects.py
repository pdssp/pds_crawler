# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Module Name:
    pds_archive

Description:
    the pds_archive module parses the PDS3 catalogs by providing the parser and stores
    the information in tha appropriate model.

Classes:
    PdsTransformer :
        Common parser, used by others parsers.
    MissionCatalogTransformer :
        Parses the PDS3 mission catalog file that contains the mission information
        and stores the information in the MissionModel class.
    ReferenceCatalogTransformer :
        Parses the PDS3 reference catalog file that contains the citations and
        stores the information in the ReferencesModel class.
    PersonCatalogTransformer :
        Parses the PDS3 person catalog file that contains the points of contact and
        stores the information in the PersonnelsModel model.
    VolumeDescriptionTransformer :
        Parses the PDS3 volume catalog file that contains the references to others
        catalogs and stores the information in the VolumeModel model.
    InstrumentCatalogTransformer :
        Parses the PDS3 instrument catalog file that contains the instrument information
        and stores the information in the InstrumentModel model.
    InstrumentHostCatalogTransformer :
        Parses the PDS3 platform catalog file that contains the platform description
        and stores the information in the InstrumentHostModel model.
    DataSetCatalogTransformer :
        Parses the PDS3 dataset catalog file that contains the dataset description
        and stores the information in the DataSetModel class.
    PdsParserFactory :
        Factory to select the right parser and the related Lark grammar.

Author:
    Jean-Christophe Malapert
"""
import importlib
import logging
import os
from abc import ABC
from abc import abstractproperty
from contextlib import closing
from pathlib import Path
from typing import Any
from typing import Dict

from lark import Lark
from lark import Transformer
from lark import Tree
from lark import v_args

from ..models import DataSetMapProjectionModel
from ..models import DataSetModel
from ..models import InstrumentHostModel
from ..models import InstrumentModel
from ..models import MissionModel
from ..models import PersonnelsModel
from ..models import ReferencesModel
from ..models import VolumeModel
from ..utils import GrammarEnum
from ..utils import requests_retry_session

logger = logging.getLogger(__name__)


class PdsTransformer(Transformer):
    """Common parser, used by others parsers."""

    def __init__(self, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)

    @abstractproperty
    def result(self) -> Any:
        raise NotImplementedError("Method def result(self) not implemented")

    @v_args(inline=True)
    def properties(self, *args):
        properties = dict()
        for arg in args:
            properties.update(arg)
        return properties

    @v_args(inline=True)
    def property(self, keyword, value):
        return {keyword: value}

    @v_args(inline=True)
    def keyword_property(self, name):
        return name.rstrip().lstrip()

    @v_args(inline=True)
    def value_property(self, name):
        return name

    @v_args(inline=True)
    def open_list(self, *args):
        return ""

    @v_args(inline=True)
    def close_list(self, *args):
        return ""

    @v_args(inline=True)
    def open_parenthesis(self, *args):
        return ""

    @v_args(inline=True)
    def close_parenthesis(self, *args):
        return ""

    @v_args(inline=True)
    def open_bracket(self, *args):
        return ""

    @v_args(inline=True)
    def close_bracket(self, *args):
        return ""

    @v_args(inline=True)
    def simple_value(self, name):
        return name.rstrip('"').lstrip('"')
        # if len(name) < 1000:
        #     name = name.replace("\n"," -")
        #     name = " ".join(name.split())
        # return name.rstrip('\"').lstrip('\"')

    @v_args(inline=True)
    def standard_value(self, *args):
        value = ""
        for arg in args:
            value += arg
        return value

    @v_args(inline=True)
    def tiret(self):
        return "-"

    @v_args(inline=True)
    def point(self):
        return "."

    @v_args(inline=True)
    def multi_values(self, *args):
        val_list = list()
        for arg in args:
            if arg != "":
                val_list.append(arg)
        return val_list

    @v_args(inline=True)
    def common_comma(self, name):
        return ","

    @v_args(inline=True)
    def simple_value_comma(self, name, *args):
        return name

    @v_args(inline=True)
    def string(self, name):
        return name

    @v_args(inline=True)
    def multi_lines_string(self, name):
        return name

    @v_args(inline=True)
    def date_str(self, *args):
        return "".join(args)


class ProjectionDescriptionTransformer(PdsTransformer):
    """Parses the PDS3 projection catalog file that contains projection information."""

    def __init__(self, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)
        self.__result: DataSetMapProjectionModel

    @property
    def result(self) -> DataSetMapProjectionModel:
        return self.__result

    @v_args(inline=True)
    def data_set_map_projection(
        self, start, properties, data_set_map_projection_info, stop
    ):
        projection = dict()
        projection.update(properties)
        projection.update(data_set_map_projection_info)
        self.__result = DataSetMapProjectionModel.from_dict(projection)

    @v_args(inline=True)
    def data_set_map_projection_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_map_projection_stop(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_map_projection_info(
        self, start, properties, data_set_map_projection_refs_info, stop
    ):
        properties.update(data_set_map_projection_refs_info)
        return {"DATA_SET_MAP_PROJECTION_INFO": properties}

    @v_args(inline=True)
    def data_set_map_projection_info_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_map_projection_info_stop(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_map_projection_refs_info(self, *args):
        return {"DS_MAP_PROJECTION_REF_INFO": args}

    @v_args(inline=True)
    def data_set_map_projection_ref_info(self, start, properties, stop):
        return properties

    @v_args(inline=True)
    def data_set_map_projection_ref_info_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_map_projection_ref_info_stop(self, *args):
        return ""


class MissionCatalogTransformer(PdsTransformer):
    """Parses the PDS3 mission catalog file that contains the mission information
    and stores the information in the MissionModel class.
    """

    def __init__(self, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)
        self.__result: MissionModel

    @property
    def result(self) -> MissionModel:
        return self.__result

    @v_args(inline=True)
    def mission(
        self,
        start,
        properties,
        mission_information,
        mission_host,
        mission_reference_informations,
        stop,
    ):
        mission = dict()
        mission.update(properties)
        mission.update(mission_information)
        mission.update(mission_host)
        mission.update(mission_reference_informations)
        self.__result = MissionModel.from_dict(mission)

    @v_args(inline=True)
    def mission_start(self, *args):
        return ""

    @v_args(inline=True)
    def mission_stop(self, *args):
        return ""

    @v_args(inline=True)
    def mission_information(self, start, properties, stop):
        return {"MISSION_INFORMATION": properties}

    @v_args(inline=True)
    def mission_information_start(self, *args):
        return ""

    @v_args(inline=True)
    def mission_information_stop(self, *args):
        return ""

    @v_args(inline=True)
    def mission_host(self, start, properties, mission_targets, stop):
        properties.update(mission_targets)
        return {"MISSION_HOST": properties}

    @v_args(inline=True)
    def mission_host_start(self, *args):
        return ""

    @v_args(inline=True)
    def mission_host_stop(self, *args):
        return ""

    @v_args(inline=True)
    def mission_targets(self, *args):
        return {"MISSION_TARGET": args}

    @v_args(inline=True)
    def mission_target(self, start, properties, stop):
        return properties

    @v_args(inline=True)
    def mission_target_start(self, *args):
        return ""

    @v_args(inline=True)
    def mission_target_stop(self, *args):
        return ""

    @v_args(inline=True)
    def mission_reference_informations(self, *args):
        return {"MISSION_REFERENCE_INFORMATION": args}

    @v_args(inline=True)
    def mission_reference_information(self, start, properties, stop):
        return properties

    @v_args(inline=True)
    def mission_reference_information_start(self, *args):
        return ""

    @v_args(inline=True)
    def mission_reference_information_stop(self, *args):
        return ""


class ReferenceCatalogTransformer(PdsTransformer):
    """Parses the PDS3 reference catalog file that contains the citations and
    stores the information in the ReferencesModel class.
    """

    def __init__(self, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)
        self.__result: ReferencesModel

    @property
    def result(self) -> ReferencesModel:
        return self.__result

    @v_args(inline=True)
    def references(self, *args):
        self.__result = ReferencesModel.from_dict({"REFERENCES": args})

    @v_args(inline=True)
    def reference(self, start, properties, stop):
        return properties

    @v_args(inline=True)
    def reference_start(*args):
        return ""

    @v_args(inline=True)
    def reference_stop(*args):
        return ""


class PersonCatalogTransformer(PdsTransformer):
    """Parses the PDS3 person catalog file that contains the points of contact and
    stores the information in the PersonnelsModel model.
    """

    def __init__(self, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)
        self.__result: PersonnelsModel

    @property
    def result(self) -> PersonnelsModel:
        return self.__result

    @v_args(inline=True)
    def personnels(self, *args):
        self.__result = PersonnelsModel.from_dict({"PERSONNELS": args})

    @v_args(inline=True)
    def personnel(
        self,
        start,
        pds_user_id,
        personnel_information,
        personnel_electronic_mail,
        stop,
    ):
        personnel = dict()
        personnel.update(pds_user_id)
        personnel.update(personnel_information)
        personnel.update(personnel_electronic_mail)
        return personnel

    @v_args(inline=True)
    def personnel_start(self, *args):
        return ""

    @v_args(inline=True)
    def personnel_stop(self, *args):
        return ""

    @v_args(inline=True)
    def pds_user_value(self, name):
        return name

    @v_args(inline=True)
    def pds_user_id(self, name):
        return {"PDS_USER_ID": name}

    @v_args(inline=True)
    def personnel_information(self, start, properties, stop):
        return {"PERSONNEL_INFORMATION": properties}

    @v_args(inline=True)
    def personnel_information_stop(self, *args):
        return ""

    @v_args(inline=True)
    def personnel_information_start(self, *args):
        return ""

    @v_args(inline=True)
    def personnel_electronic_mail(self, start, name, stop):
        return {"PERSONNEL_ELECTRONIC_MAIL": name}

    @v_args(inline=True)
    def personnel_electronic_mail_stop(self, *args):
        return ""

    @v_args(inline=True)
    def personnel_electronic_mail_start(self, *args):
        return ""


class VolumeDescriptionTransformer(PdsTransformer):
    """Parses the PDS3 volume catalog file that contains the references to others
    catalogs and stores the information in the VolumeModel model.
    """

    def __init__(self, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)
        self.__result: VolumeModel

    @property
    def result(self) -> VolumeModel:
        return self.__result

    @v_args(inline=True)
    def volume(self, *args):
        volume = dict()
        for arg in args:
            if isinstance(arg, Tree):
                # this is start or stop
                continue
            volume.update(arg)
        self.__result = VolumeModel.from_dict(volume)

    @v_args(inline=True)
    def volume_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_producer(self, start, properties, stop):
        return {"DATA_PRODUCER": properties}

    @v_args(inline=True)
    def data_producer_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_producer_stop(self, *args):
        return ""

    @v_args(inline=True)
    def catalog(self, start, properties, stop):
        return {"CATALOG": properties}

    @v_args(inline=True)
    def catalog_start(self, *args):
        return ""

    @v_args(inline=True)
    def catalog_stop(self, *args):
        return ""

    @v_args(inline=True)
    def data_supplier(self, start, properties, stop):
        return {"DATA_SUPPLIER": properties}

    @v_args(inline=True)
    def data_supplier_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_supplier_stop(self, *args):
        return ""

    @v_args(inline=True)
    def files(self, *args):
        return {"FILE": args}

    @v_args(inline=True)
    def file(self, start, properties, stop):
        return properties

    @v_args(inline=True)
    def file_start(self, *args):
        return ""

    @v_args(inline=True)
    def file_stop(self, *args):
        return ""

    @v_args(inline=True)
    def directories(self, *args):
        return {"DIRECTORY": args}

    @v_args(inline=True)
    def directory(self, start, properties, files, stop):
        properties.update(files)
        return properties

    @v_args(inline=True)
    def directory_start(self, *args):
        return ""

    @v_args(inline=True)
    def directory_stop(self, *args):
        return ""


class InstrumentCatalogTransformer(PdsTransformer):
    """Parses the PDS3 platform catalog file that contains the platform description
    and stores the information in the InstrumentHostModel model.
    """

    def __init__(self, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)
        self.__result: InstrumentModel

    @property
    def result(self) -> InstrumentModel:
        return self.__result

    @v_args(inline=True)
    def instrument(
        self,
        start,
        properties,
        instrument_information,
        instrument_reference_infos,
        stop,
    ):
        instrument = dict()
        instrument.update(properties)
        instrument.update(instrument_information)
        instrument.update(instrument_reference_infos)
        self.__result = InstrumentModel.from_dict(instrument)

    @v_args(inline=True)
    def instrument_start(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_stop(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_information(self, start, properties, stop):
        return {"INSTRUMENT_INFORMATION": properties}

    @v_args(inline=True)
    def instrument_information_start(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_information_stop(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_reference_infos(self, *args):
        return {"INSTRUMENT_REFERENCE_INFO": args}

    @v_args(inline=True)
    def instrument_reference_info(self, start, properties, stop):
        return properties

    @v_args(inline=True)
    def instrument_reference_info_start(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_reference_info_stop(self, *args):
        return ""


class InstrumentHostCatalogTransformer(PdsTransformer):
    """Parses the PDS3 platform catalog file that contains the platform description
    and stores the information in the InstrumentHostModel model.
    """

    def __init__(self, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)
        self.__result: InstrumentHostModel

    @property
    def result(self) -> InstrumentHostModel:
        return self.__result

    @v_args(inline=True)
    def instrument_host(
        self,
        start,
        properties,
        instrument_host_information,
        instrument_host_reference_infos,
        stop,
    ):
        instrument_host = dict()
        instrument_host.update(properties)
        instrument_host.update(instrument_host_information)
        instrument_host.update(instrument_host_reference_infos)
        self.__result = InstrumentHostModel.from_dict(instrument_host)

    @v_args(inline=True)
    def instrument_host_start(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_host_stop(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_host_information(self, start, properties, stop):
        return {"INSTRUMENT_HOST_INFORMATION": properties}

    @v_args(inline=True)
    def instrument_host_information_start(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_host_information_stop(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_host_reference_infos(self, *args):
        return {"INSTRUMENT_HOST_REFERENCE_INFO": args}

    @v_args(inline=True)
    def instrument_host_reference_info(self, start, properties, stop):
        return properties

    @v_args(inline=True)
    def instrument_host_reference_info_start(self, *args):
        return ""

    @v_args(inline=True)
    def instrument_host_reference_info_stop(self, *args):
        return ""


class DataSetCatalogTransformer(PdsTransformer):
    """Parses the PDS3 dataset catalog file that contains the dataset description
    and stores the information in the DataSetModel class.
    """

    def __init__(self, visit_tokens: bool = True) -> None:
        super().__init__(visit_tokens)
        self.__result: DataSetModel

    @property
    def result(self) -> DataSetModel:
        return self.__result

    @v_args(inline=True)
    def data_set_content(self, *args):
        dataset = dict()
        for arg in args:
            dataset.update(arg)
        return dataset

    @v_args(inline=True)
    def data_set(self, *args):
        dataset = dict()
        for arg in args:
            dataset.update(arg)
        self.__result = DataSetModel.from_dict(dataset)

    @v_args(inline=True)
    def data_set_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_stop(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_host(self, start, properties, stop):
        return {"DATA_SET_HOST": properties}

    @v_args(inline=True)
    def data_set_host_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_host_stop(self, *args):
        return ""

    @v_args(inline=True)
    def dataset_information(self, start, properties, stop):
        return {"DATA_SET_INFORMATION": properties}

    @v_args(inline=True)
    def dataset_information_start(self, *args):
        return ""

    @v_args(inline=True)
    def dataset_information_stop(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_targets(self, *args):
        return {"DATA_SET_TARGET": args}

    @v_args(inline=True)
    def data_set_target(self, start, properties, stop):
        return properties

    @v_args(inline=True)
    def data_set_target_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_target_stop(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_mission(self, start, properties, stop):
        return {"DATA_SET_MISSION": properties}

    @v_args(inline=True)
    def data_set_mission_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_mission_stop(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_reference_informations(self, *args):
        return {"DATA_SET_REFERENCE_INFORMATION".upper(): args}

    @v_args(inline=True)
    def data_set_reference_information(self, start, properties, stop):
        return properties

    @v_args(inline=True)
    def data_set_reference_information_start(self, *args):
        return ""

    @v_args(inline=True)
    def data_set_reference_information_stop(self, *args):
        return ""


class PdsParserFactory(ABC):
    """Factory to select the right parser and the related Lark grammar."""

    class FileGrammary(GrammarEnum):
        """Mapping between enum, Lark grammar and implementation class."""

        REFERENCE_CATALOG = (
            "REFERENCE_CATALOG",
            "grammar_ref_cat.lark",
            "ReferenceCatalogTransformer",
            "Grammary for reference catalog",
        )
        MISSION_CATALOG = (
            "MISSION_CATALOG",
            "grammar_mission_cat.lark",
            "MissionCatalogTransformer",
            "Grammary for mission catalog",
        )
        PERSONNEL_CATALOG = (
            "PERSONNEL_CATALOG",
            "grammar_person_cat.lark",
            "PersonCatalogTransformer",
            "Grammary for person catalog",
        )
        INSTRUMENT_CATALOG = (
            "INSTRUMENT_CATALOG",
            "grammar_inst_cat.lark",
            "InstrumentCatalogTransformer",
            "Grammary for instrument catalog",
        )
        INSTRUMENT_HOST_CATALOG = (
            "INSTRUMENT_HOST_CATALOG",
            "grammar_inst_host.lark",
            "InstrumentHostCatalogTransformer",
            "Grammary for instrument host catalog",
        )
        DATA_SET_CATALOG = (
            "DATA_SET_CATALOG",
            "grammar_ds_cat.lark",
            "DataSetCatalogTransformer",
            "Grammary for dataset catalog",
        )
        VOL_DESC = (
            "VOL_DESC",
            "grammar_vol_desc.lark",
            "VolumeDescriptionTransformer",
            "Grammary for volume description",
        )
        DATA_SET_MAP_PROJECTION_CATALOG = (
            "DATA_SET_MAP_PROJECTION_CATALOG",
            "grammar_projection.lark",
            "ProjectionDescriptionTransformer",
            "Grammary for volume description",
        )

        @staticmethod
        def get_enum_from(name: str):
            members = PdsParserFactory.FileGrammary._member_map_
            if name in members:
                return members[name]
            else:
                raise KeyError(f"File Grammary enum not found from {name}")

    @staticmethod
    def parse(uri: str, type_file: FileGrammary, **args) -> Any:
        """Parse the content of a file provided an URI by using a Lark grammar.

        Args:
            uri (str): URI of the file or directly content of the file
            type_file (FileGrammary): Type of file

        Raises:
            NotImplementedError: Unknown implementation class

        Note: Other arguments will be passed to json dump (like indent=4)

        Returns:
            Any: One of the models
        """
        parser: Lark
        content: str
        if Path(uri).is_file:
            with open(uri, encoding="utf8", errors="ignore") as f:
                content = f.read()
        elif uri.lower().startswith("http"):
            with closing(
                requests_retry_session().get(
                    uri, stream=True, verify=False, timeout=(180, 1800)
                )
            ) as response:
                if response.ok:
                    content = response.text
                else:
                    raise Exception(uri)
        else:
            content = uri

        grammary_file: str = os.path.join(
            os.path.abspath(os.path.dirname(__file__)),
            "grammar",
            type_file.grammar,
        )
        parser = Lark.open(grammary_file, rel_to=__file__)
        try:
            module = importlib.import_module(__name__)
            transformer: PdsTransformer = getattr(
                module, type_file.class_name
            )()
            transformer.transform(parser.parse(content))
            return transformer.result
        except ModuleNotFoundError:
            raise NotImplementedError(
                "Cannot load data products plugin with "
                + __name__
                + "."
                + type_file.class_name
            )
