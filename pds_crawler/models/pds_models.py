# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""PDS models for catalogs"""
import inspect
from dataclasses import dataclass
from dataclasses import field
from datetime import datetime
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Union

import pystac

from ..utils import utc_to_iso
from .common import AbstractModel


@dataclass(frozen=True, eq=True)
class ReferenceModel(AbstractModel):
    REFERENCE_KEY_ID: str
    REFERENCE_DESC: str = field(repr=False, compare=False)


@dataclass(frozen=True, eq=True)
class ReferencesModel(AbstractModel):
    REFERENCES: List[ReferenceModel]

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "REFERENCES" in data:
            data["REFERENCES"] = [
                ReferenceModel.from_dict(elem) for elem in data["REFERENCES"]
            ]
        return cls(**{k: v for k, v in data.items()})


@dataclass(frozen=True, eq=True)
class DataSetInformationModel(AbstractModel):
    CONFIDENCE_LEVEL_NOTE: str = field(repr=False, compare=False)
    DATA_SET_COLLECTION_MEMBER_FLG: str = field(repr=False, compare=False)
    DATA_SET_DESC: str = field(repr=False, compare=False)
    DATA_SET_NAME: str
    DATA_SET_RELEASE_DATE: str
    DETAILED_CATALOG_FLAG: str = field(repr=False, compare=False)
    PRODUCER_FULL_NAME: Union[str, List[str]] = field(
        repr=False, compare=False
    )
    START_TIME: str = field(repr=False, compare=False)
    STOP_TIME: str = field(repr=False, compare=False)
    DATA_OBJECT_TYPE: str = field(default=None, repr=False, compare=False)
    ABSTRACT_DESC: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    CITATION_DESC: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    DATA_SET_TERSE_DESC: Optional[str] = field(
        default=None, repr=False, compare=False
    )

    def _get_title(self) -> str:
        return self.DATA_SET_NAME

    def _get_description(self) -> Optional[str]:
        description: Optional[str] = None
        if self.ABSTRACT_DESC:
            description = self.ABSTRACT_DESC
        elif self.DATA_SET_DESC:
            description = self.DATA_SET_DESC
        return description

    def _add_providers(self, stac_collection: pystac.Collection):
        if isinstance(self.PRODUCER_FULL_NAME, list):
            stac_collection.providers = [
                pystac.Provider(
                    name=provider, roles=[pystac.ProviderRole.PRODUCER]
                )
                for provider in self.PRODUCER_FULL_NAME
            ]
        else:
            stac_collection.providers = [
                pystac.Provider(
                    name=self.PRODUCER_FULL_NAME,
                    roles=[pystac.ProviderRole.PRODUCER],
                )
            ]

    def _add_citations(self, stac_collection: pystac.Collection):
        if self.CITATION_DESC:
            stac_collection.summaries.add(
                "sci:publications", {"sci:citation": self.CITATION_DESC}
            )
            stac_collection.stac_extensions.append(
                "https://stac-extensions.github.io/scientific/v1.0.0/schema.json"
            )

    def _get_start_date(self) -> Optional[datetime]:
        start_date = Optional[datetime]
        try:
            start_date = datetime.strptime(utc_to_iso(self.START_TIME))
        except:  # noqa: E722
            start_date = None
        return start_date

    def _get_stop_date(self) -> Optional[datetime]:
        stop_date = Optional[datetime]
        try:
            stop_date = datetime.strptime(utc_to_iso(self.STOP_TIME))
        except:  # noqa: E722
            stop_date = None
        return stop_date

    def _get_range_time(self) -> Optional[pystac.RangeSummary]:
        range: Optional[pystac.RangeSummary] = None
        start_date = self._get_start_date()
        stop_date = self._get_stop_date()
        if start_date is not None and stop_date is not None:
            range = pystac.RangeSummary(minimum=start_date, maximum=stop_date)
        return range

    def _set_extent(self, stac_collection: pystac.Collection):
        stac_collection.extent = pystac.Extent(
            pystac.SpatialExtent(bboxes=[[]]),
            pystac.TemporalExtent(
                intervals=[[self._get_start_date(), self._get_stop_date()]]
            ),
        )

    def _add_summaries(self, stac_collection: pystac.Collection):
        summaries: Dict[str, Any] = dict()
        range_time = self._get_range_time()

        if stac_collection.summaries and range_time is not None:
            stac_collection.summaries["observation_time"] = range_time
        elif stac_collection.summaries is None and range_time is not None:
            stac_collection.summaries = pystac.Summaries(summaries=summaries)

    def _add_extra_kwds(self, stac_collection: pystac.Collection):
        extra_kws = {
            attribute.lower(): self.__dict__[attribute]
            for attribute in self.__dict__.keys()
            if attribute
            in [
                "CONFIDENCE_LEVEL_NOTE",
                "DATA_SET_COLLECTION_MEMBER_FLG",
                "DETAILED_CATALOG_FLAG",
                "DATA_OBJECT_TYPE",
                "DATA_SET_RELEASE_DATE" "CITATION_DESC",
            ]
            and attribute is not None
        }
        if stac_collection.extra_fields:
            stac_collection.extra_fields.update(extra_kws)
        else:
            stac_collection.extra_fields = extra_kws

    @classmethod
    def from_dict(cls, env):
        parameters = inspect.signature(cls).parameters
        return cls(**{k: v for k, v in env.items() if k in parameters})

    def update_stac(self, stac_collection: pystac.Collection):
        stac_collection.title = self._get_title()
        if self._get_description():
            stac_collection.description = self._get_description()

        self._set_extent(stac_collection)
        self._add_providers(stac_collection)
        self._add_citations(stac_collection)
        self._add_summaries(stac_collection)
        self._add_extra_kwds(stac_collection)


@dataclass(frozen=True, eq=True)
class DataSetTargetModel(AbstractModel):
    TARGET_NAME: str

    @classmethod
    def from_dict(cls, env):
        parameters = inspect.signature(cls).parameters
        return cls(**{k: v for k, v in env.items() if k in parameters})

    def update_stac(self, stac_collection: pystac.Collection):
        if not stac_collection.extra_fields:
            stac_collection.extra_fields = dict()
        stac_collection.extra_fields["ssys:targets"] = self.TARGET_NAME
        stac_collection.stac_extensions.append(
            "https://github.com/thareUSGS/ssys/blob/main/json-schema/schema.json"
        )


@dataclass(frozen=True, eq=True)
class DataSetHostModel(AbstractModel):
    INSTRUMENT_HOST_ID: str
    INSTRUMENT_ID: str

    def get_instrument_id(self):
        return f"urn:pdssp:pds:instru:{self.INSTRUMENT_ID}"

    def get_plateform_id(self):
        return f"urn:pdssp:pds:plateform:{self.INSTRUMENT_HOST_ID}"

    def update_stac(self, stac_collection: pystac.Collection):
        if not stac_collection.extra_fields:
            stac_collection.extra_fields = dict()
        stac_collection.extra_fields["plateform_id"] = self.INSTRUMENT_HOST_ID
        stac_collection.extra_fields["instrument_id"] = self.INSTRUMENT_ID


@dataclass(frozen=True, eq=True)
class DataSetMissionModel(AbstractModel):
    MISSION_NAME: str

    def update_stac(self, stac_collection: pystac.Collection):
        if not stac_collection.extra_fields:
            stac_collection.extra_fields = dict()
        stac_collection.extra_fields["mission"] = self.MISSION_NAME


@dataclass(frozen=True, eq=True)
class DataSetReferenceInformationModel(AbstractModel):
    REFERENCE_KEY_ID: str


@dataclass(frozen=True, eq=True)
class DataSetModel(AbstractModel):
    DATA_SET_ID: str
    DATA_SET_INFORMATION: DataSetInformationModel = field(
        repr=False, compare=False
    )
    DATA_SET_TARGET: List[DataSetTargetModel] = field(
        repr=False, compare=False
    )
    DATA_SET_HOST: DataSetHostModel = field(repr=False, compare=False)
    DATA_SET_REFERENCE_INFORMATION: List[
        DataSetReferenceInformationModel
    ] = field(repr=False, compare=False)
    DATA_SET_MISSION: DataSetMissionModel = field(
        default=None, repr=False, compare=False
    )

    def collection_id(self) -> str:
        return f"urn:pdssp:pds:collection:{self.DATA_SET_ID}"

    def _add_citations(
        self,
        stac_collection: pystac.Collection,
        citations: Optional[ReferencesModel],
    ):
        if citations:
            references = {
                citation.REFERENCE_KEY_ID: citation.REFERENCE_DESC
                for citation in citations.REFERENCES
                if citation.REFERENCE_KEY_ID is not None
            }
            publi_list = [
                references.get(citation)
                for citation in self.DATA_SET_REFERENCE_INFORMATION
                if references.get(citation) is not None
            ]
            if stac_collection.extra_fields:
                stac_collection.extra_fields.update({})
            stac_collection.extra_fields = {"sci:publications": publi_list}

    def _add_providers(
        self,
        stac_collection: pystac.Collection,
        data_supplier: "DataSupplierModel",
        data_producer: "DataProducerModel",
    ):
        providers: List[pystac.Provider] = list()
        if data_supplier:
            providers.append(data_supplier.create_stac_data_provider())
        if data_producer:
            providers.append(data_producer.create_stac_data_provider())
        stac_collection.providers = providers

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "DATA_SET_INFORMATION" in data:
            data["DATA_SET_INFORMATION"] = DataSetInformationModel.from_dict(
                data["DATA_SET_INFORMATION"]
            )
        if "DATA_SET_TARGET" in data:
            data["DATA_SET_TARGET"] = [
                DataSetTargetModel.from_dict(elem)
                for elem in data["DATA_SET_TARGET"]
            ]
        if "DATA_SET_HOST" in data:
            data["DATA_SET_HOST"] = DataSetHostModel.from_dict(
                data["DATA_SET_HOST"]
            )

        if "DATA_SET_MISSION" in data:
            data["DATA_SET_MISSION"] = DataSetMissionModel.from_dict(
                data["DATA_SET_MISSION"]
            )
        if "DATA_SET_REFERENCE_INFORMATION" in data:
            data["DATA_SET_REFERENCE_INFORMATION"] = [
                DataSetReferenceInformationModel.from_dict(elem)
                for elem in data["DATA_SET_REFERENCE_INFORMATION"]
            ]
        return cls(**{k: v for k, v in data.items()})

    def create_stac_collection(
        self,
        citations: ReferencesModel,
        data_supplier: "DataSupplierModel",
        data_producer: "DataProducerModel",
    ) -> pystac.Collection:
        stac_collection = pystac.Collection(
            id=self.collection_id(),
            description="",
            extent=pystac.Extent(
                pystac.SpatialExtent(bboxes=[[]]),
                pystac.TemporalExtent(intervals=[[None, None]]),
            ),
        )
        self.DATA_SET_INFORMATION.update_stac(stac_collection)
        self.DATA_SET_TARGET[0].update_stac(stac_collection)
        self.DATA_SET_HOST.update_stac(stac_collection)

        if self.DATA_SET_MISSION:
            self.DATA_SET_MISSION.update_stac(stac_collection)

        self._add_citations(stac_collection, citations)
        self._add_providers(stac_collection, data_supplier, data_producer)
        stac_collection.license = "CC0-1.0"

        return stac_collection


@dataclass(frozen=True, eq=True)
class InstrumentReferenceInfoModel(AbstractModel):
    REFERENCE_KEY_ID: str


@dataclass(frozen=True, eq=True)
class InstrumentInformationModel(AbstractModel):
    INSTRUMENT_DESC: str = field(repr=False, compare=False)
    INSTRUMENT_NAME: str
    INSTRUMENT_TYPE: str

    def update_stac(self, stac_catalog: pystac.Catalog):
        stac_catalog.description = self.INSTRUMENT_DESC
        stac_catalog.title = self.INSTRUMENT_NAME
        if not stac_catalog.extra_fields:
            stac_catalog.extra_fields = dict()
        stac_catalog.extra_fields["instrument_type"] = self.INSTRUMENT_TYPE


@dataclass(frozen=True, eq=True)
class InstrumentModel(AbstractModel):
    INSTRUMENT_HOST_ID: str
    INSTRUMENT_ID: str
    INSTRUMENT_INFORMATION: InstrumentInformationModel = field(
        repr=False, compare=False
    )
    INSTRUMENT_REFERENCE_INFO: List[InstrumentReferenceInfoModel] = field(
        repr=False, compare=False
    )

    def get_plateform_id(self):
        return f"urn:pdssp:pds:plateform:{self.INSTRUMENT_HOST_ID}"

    def get_instrument_id(self):
        return f"urn:pdssp:pds:instru:{self.INSTRUMENT_ID}"

    def _add_citations(
        self,
        stac_catalog: pystac.Catalog,
        citations: Optional[ReferencesModel],
    ):
        if citations:
            references = {
                citation.REFERENCE_KEY_ID: citation.REFERENCE_DESC
                for citation in citations.REFERENCES
                if citation.REFERENCE_KEY_ID is not None
            }
            publi_list = [
                references.get(citation)
                for citation in self.INSTRUMENT_REFERENCE_INFO
                if references.get(citation) is not None
            ]
            if not stac_catalog.extra_fields:
                stac_catalog.extra_fields = dict()
            stac_catalog.extra_fields["publications"] = publi_list

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "INSTRUMENT_INFORMATION" in data:
            data[
                "INSTRUMENT_INFORMATION"
            ] = InstrumentInformationModel.from_dict(
                data["INSTRUMENT_INFORMATION"]
            )
        if "INSTRUMENT_REFERENCE_INFO" in data:
            data["INSTRUMENT_REFERENCE_INFO"] = [
                InstrumentReferenceInfoModel.from_dict(elem)
                for elem in data["INSTRUMENT_REFERENCE_INFO"]
            ]
        return cls(**{k: v for k, v in data.items()})

    def create_stac_catalog(
        self, citations: Optional[ReferencesModel] = None
    ) -> pystac.Catalog:
        stac_catalog = pystac.Catalog(
            title=self.INSTRUMENT_ID,
            id=self.get_instrument_id(),
            description="",
        )
        self._add_citations(stac_catalog, citations)
        self.INSTRUMENT_INFORMATION.update_stac(stac_catalog)

        return stac_catalog


@dataclass(frozen=True, eq=True)
class InstrumentHostInformationModel(AbstractModel):
    INSTRUMENT_HOST_DESC: str = field(repr=False, compare=False)
    INSTRUMENT_HOST_NAME: str
    INSTRUMENT_HOST_TYPE: str

    def update_stac(self, stac_catalog: pystac.Catalog):
        stac_catalog.description = self.INSTRUMENT_HOST_DESC
        stac_catalog.title = self.INSTRUMENT_HOST_NAME
        if not stac_catalog.extra_fields:
            stac_catalog.extra_fields = dict()
        stac_catalog.extra_fields["plateform"] = self.INSTRUMENT_HOST_TYPE


@dataclass(frozen=True, eq=True)
class InstrumentHostReferenceInfoModel(AbstractModel):
    REFERENCE_KEY_ID: str


@dataclass(frozen=True, eq=True)
class InstrumentHostModel(AbstractModel):
    INSTRUMENT_HOST_ID: str
    INSTRUMENT_HOST_INFORMATION: InstrumentHostInformationModel = field(
        repr=False, compare=False
    )
    INSTRUMENT_HOST_REFERENCE_INFO: List[
        InstrumentHostReferenceInfoModel
    ] = field(repr=False, compare=False)

    def get_plateform_id(self) -> str:
        return f"urn:pdssp:pds:plateform:{self.INSTRUMENT_HOST_ID}"

    def _add_citations(
        self,
        stac_catalog: pystac.Catalog,
        citations: Optional[ReferencesModel],
    ):
        if citations:
            references = {
                citation.REFERENCE_KEY_ID: citation.REFERENCE_DESC
                for citation in citations.REFERENCES
                if citation.REFERENCE_KEY_ID is not None
            }
            publi_list = [
                references.get(citation)
                for citation in self.INSTRUMENT_HOST_REFERENCE_INFO
                if references.get(citation) is not None
            ]
            if not stac_catalog.extra_fields:
                stac_catalog.extra_fields = dict()
            stac_catalog.extra_fields["publications"] = publi_list

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "INSTRUMENT_HOST_INFORMATION" in data:
            data[
                "INSTRUMENT_HOST_INFORMATION"
            ] = InstrumentHostInformationModel.from_dict(
                data["INSTRUMENT_HOST_INFORMATION"]
            )
        if "INSTRUMENT_HOST_REFERENCE_INFO" in data:
            data["INSTRUMENT_HOST_REFERENCE_INFO"] = [
                InstrumentHostReferenceInfoModel.from_dict(elem)
                for elem in data["INSTRUMENT_HOST_REFERENCE_INFO"]
            ]
        return cls(**{k: v for k, v in data.items()})

    def create_stac_catalog(
        self, citations: Optional[ReferencesModel] = None
    ) -> pystac.Catalog:
        stac_catalog = pystac.Catalog(
            title=self.INSTRUMENT_HOST_ID,
            id=self.get_plateform_id(),
            description="",
        )
        self._add_citations(stac_catalog, citations)
        self.INSTRUMENT_HOST_INFORMATION.update_stac(stac_catalog)

        return stac_catalog


@dataclass(frozen=True, eq=True)
class MissionInformationModel(AbstractModel):
    MISSION_ALIAS_NAME: str
    MISSION_DESC: str = field(repr=False, compare=False)
    MISSION_OBJECTIVES_SUMMARY: str = field(repr=False, compare=False)
    MISSION_START_DATE: str
    MISSION_STOP_DATE: str

    def get_mission_id(self):
        return f"urn:pdssp:pds:mission:{self.MISSION_ALIAS_NAME}"

    @classmethod
    def from_dict(cls, env):
        data = env.copy()
        # Fix problem
        if data["MISSION_ALIAS_NAME"] == "N/A":
            data["MISSION_ALIAS_NAME"] = "MGS"
        return cls(**{k: v for k, v in data.items()})

    def update_stac(self, stac_catalog: pystac.Catalog):
        stac_catalog.description = self.MISSION_DESC
        stac_catalog.id = self.get_mission_id()
        if not stac_catalog.extra_fields:
            stac_catalog.extra_fields = dict()
        stac_catalog.extra_fields[
            "mission_objectives_summary"
        ] = self.MISSION_OBJECTIVES_SUMMARY
        stac_catalog.extra_fields[
            "mission_start_date"
        ] = self.MISSION_START_DATE
        stac_catalog.extra_fields["mission_stop_date"] = self.MISSION_STOP_DATE


@dataclass(frozen=True, eq=True)
class MissionTargetModel(AbstractModel):
    TARGET_NAME: str

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "MISSION_TARGET" in data:
            data["MISSION_TARGET"] = [
                MissionTargetModel.from_dict(elem)
                for elem in data["MISSION_TARGET"]
            ]
        return cls(**{k: v for k, v in data.items()})


@dataclass(frozen=True, eq=True)
class MissionHostModel(AbstractModel):
    INSTRUMENT_HOST_ID: str
    MISSION_TARGET: List[MissionTargetModel]

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "MISSION_TARGET" in data:
            data["MISSION_TARGET"] = [
                MissionTargetModel.from_dict(elem)
                for elem in data["MISSION_TARGET"]
            ]
        return cls(**{k: v for k, v in data.items()})

    def update_stac(self, stac_catalog: pystac.Catalog):
        if not stac_catalog.extra_fields:
            stac_catalog.extra_fields = dict()
        stac_catalog.extra_fields["plateform_id"] = self.INSTRUMENT_HOST_ID
        stac_catalog.extra_fields["mission_targets"] = [
            mission_target.TARGET_NAME
            for mission_target in self.MISSION_TARGET
        ]


@dataclass(frozen=True, eq=True)
class MissionReferenceInformationModel(AbstractModel):
    REFERENCE_KEY_ID: str


@dataclass(frozen=True, eq=True)
class DataSetMapProjectionRefInfoModel(AbstractModel):
    REFERENCE_KEY_ID: str


@dataclass(frozen=True, eq=True)
class DataSetMapProjectionInfoModel(AbstractModel):
    MAP_PROJECTION_DESC: str = field(repr=False, compare=False)
    MAP_PROJECTION_TYPE: str
    ROTATIONAL_ELEMENT_DESC: str = field(repr=False, compare=False)
    DS_MAP_PROJECTION_REF_INFO: List[DataSetMapProjectionRefInfoModel] = field(
        repr=False, compare=False
    )


@dataclass(frozen=True, eq=True)
class DataSetMapProjectionModel(AbstractModel):
    DATA_SET_ID: str
    DATA_SET_MAP_PROJECTION_INFO: DataSetMapProjectionInfoModel = field(
        repr=False, compare=False
    )


@dataclass(frozen=True, eq=True)
class MissionModel(AbstractModel):
    MISSION_NAME: str
    MISSION_HOST: MissionHostModel
    MISSION_INFORMATION: MissionInformationModel = field(
        repr=False, compare=False
    )
    MISSION_REFERENCE_INFORMATION: List[
        MissionReferenceInformationModel
    ] = field(repr=False, compare=False)

    def _add_citations(
        self,
        stac_catalog: pystac.Catalog,
        citations: Optional[ReferencesModel],
    ):
        if citations:
            references = {
                citation.REFERENCE_KEY_ID: citation.REFERENCE_DESC
                for citation in citations.REFERENCES
                if citation.REFERENCE_KEY_ID is not None
            }
            publi_list = [
                references.get(citation)
                for citation in self.MISSION_REFERENCE_INFORMATION
                if references.get(citation) is not None
            ]
            if not stac_catalog.extra_fields:
                stac_catalog.extra_fields = dict()
            stac_catalog.extra_fields["publications"]: publi_list

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "MISSION_HOST" in data:
            data["MISSION_HOST"] = MissionHostModel.from_dict(
                data["MISSION_HOST"]
            )
        if "MISSION_INFORMATION" in data:
            data["MISSION_INFORMATION"] = MissionInformationModel.from_dict(
                data["MISSION_INFORMATION"]
            )
        if "MISSION_REFERENCE_INFORMATION" in data:
            data["MISSION_REFERENCE_INFORMATION"] = [
                MissionReferenceInformationModel.from_dict(elem)
                for elem in data["MISSION_REFERENCE_INFORMATION"]
            ]
        parameters = inspect.signature(cls).parameters
        return cls(**{k: v for k, v in data.items() if k in parameters})

    def create_stac_catalog(
        self, citations: Optional[ReferencesModel] = None
    ) -> pystac.Catalog:
        stac_catalog = pystac.Catalog(
            title=self.MISSION_NAME, id="", description=""
        )
        self.MISSION_HOST.update_stac(stac_catalog)
        self.MISSION_INFORMATION.update_stac(stac_catalog)

        return stac_catalog


@dataclass(frozen=True, eq=True)
class PersonnelInformationModel(AbstractModel):
    ADDRESS_TEXT: str = field(repr=False, compare=False)
    ALTERNATE_TELEPHONE_NUMBER: str = field(repr=False, compare=False)
    FAX_NUMBER: str = field(repr=False, compare=False)
    FULL_NAME: str
    INSTITUTION_NAME: str
    LAST_NAME: str
    NODE_ID: str = field(repr=False)
    PDS_AFFILIATION: str = field(repr=False, compare=False)
    REGISTRATION_DATE: str = field(repr=False, compare=False)
    TELEPHONE_NUMBER: str = field(repr=False, compare=False)
    PDS_ADDRESS_BOOK_FLAG: Optional[str] = field(
        default=None, repr=False, compare=False
    )


@dataclass(frozen=True, eq=True)
class PersonnelElectronicMailModel(AbstractModel):
    ELECTRONIC_MAIL_ID: str
    ELECTRONIC_MAIL_TYPE: str = field(repr=False, compare=False)
    PREFERENCE_ID: str = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, eq=True)
class PersonnelModel(AbstractModel):
    PDS_USER_ID: str
    PERSONNEL_ELECTRONIC_MAIL: PersonnelElectronicMailModel = field(
        repr=False, compare=False
    )
    PERSONNEL_INFORMATION: PersonnelInformationModel = field(
        repr=False, compare=False
    )

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "PERSONNEL_ELECTRONIC_MAIL" in data:
            data[
                "PERSONNEL_ELECTRONIC_MAIL"
            ] = PersonnelElectronicMailModel.from_dict(
                data["PERSONNEL_ELECTRONIC_MAIL"]
            )
        if "PERSONNEL_INFORMATION" in data:
            data[
                "PERSONNEL_INFORMATION"
            ] = PersonnelInformationModel.from_dict(
                data["PERSONNEL_INFORMATION"]
            )
        return cls(**{k: v for k, v in data.items()})


@dataclass(frozen=True, eq=True)
class PersonnelsModel(AbstractModel):
    PERSONNELS: List[PersonnelModel]

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "PERSONNELS" in data:
            data["PERSONNELS"] = [
                PersonnelModel.from_dict(elem) for elem in data["PERSONNELS"]
            ]
        return cls(**{k: v for k, v in data.items()})


@dataclass(frozen=True, eq=True)
class CatalogModel(AbstractModel):
    DATA_SET_CATALOG: Optional[Union[str, List[str]]] = field(
        default=None, repr=False, compare=False
    )
    INSTRUMENT_CATALOG: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    INSTRUMENT_HOST_CATALOG: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    MISSION_CATALOG: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    LOGICAL_VOLUME_PATHNAME: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    LOGICAL_VOLUMES: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    DATA_SET_ID: Optional[str] = field(default=None, repr=False, compare=False)
    DATA_SET_COLLECTION_CATALOG: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    PERSONNEL_CATALOG: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    REFERENCE_CATALOG: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    TARGET_CATALOG: Optional[str] = field(
        default=None, repr=False, compare=False
    )

    @classmethod
    def from_dict(cls, env: Dict):
        parameters = inspect.signature(cls).parameters
        return cls(**{k: v for k, v in env.items() if k in parameters})


@dataclass(frozen=True, eq=True)
class DataProducerModel(AbstractModel):
    INSTITUTION_NAME: str
    FACILITY_NAME: str
    FULL_NAME: str
    ADDRESS_TEXT: str = field(repr=False, compare=False)
    DISCIPLINE_NAME: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    NODE_NAME: Optional[str] = field(default=None, repr=False, compare=False)
    TELEPHONE_NUMBER: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    ELECTRONIC_MAIL_TYPE: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    ELECTRONIC_MAIL_ID: Optional[str] = field(
        default=None, repr=False, compare=False
    )

    def create_stac_data_provider(self) -> pystac.Provider:
        producer = pystac.Provider(
            name=self.FULL_NAME, roles=[pystac.ProviderRole.HOST]
        )
        producer.extra_fields = {
            key.lower(): self.__dict__[key]
            for key in self.__dict__.keys()
            if key is not None and key not in ["FULL_NAME"]
        }
        return producer


@dataclass(frozen=True, eq=True)
class FileModel(AbstractModel):
    RECORD_TYPE: str
    DESCRIPTION: Optional[str] = field(default=None, repr=False, compare=False)
    ENCODING_TYPE: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    FILE_NAME: Optional[str] = field(default=None, repr=False)
    FILE_RECORDS: Optional[str] = field(default=None, repr=False)
    INTERCHANGE_FORMAT: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    LABEL_RECORDS: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    RECORD_BYTES: Optional[str] = field(default=None, repr=False)
    REQUIRED_STORAGE_BYTES: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    SEQUENCE_NUMBER: Optional[str] = field(default=None, repr=False)
    UNCOMPRESSED_FILE_NAME: Optional[str] = field(
        default=None, repr=False, compare=False
    )


@dataclass(frozen=True, eq=True)
class DirectoryModel(AbstractModel):
    NAME: str
    FILE: List[FileModel] = field(repr=False)
    RECORD_TYPE: Optional[str] = field(default=None, repr=False, compare=False)
    SEQUENCE_NUMBER: Optional[str] = field(
        default=None, repr=False, compare=False
    )

    @classmethod
    def from_dict(cls, env: Dict):
        data = env.copy()
        if "FILE" in data:
            data["FILE"] = [FileModel.from_dict(elem) for elem in data["FILE"]]
        return cls(**{k: v for k, v in data.items()})


@dataclass(frozen=True, eq=True)
class DataSupplierModel(AbstractModel):
    INSTITUTION_NAME: str
    FACILITY_NAME: str
    FULL_NAME: str
    ADDRESS_TEXT: str = field(repr=False, compare=False)
    TELEPHONE_NUMBER: str = field(repr=False, compare=False)
    ELECTRONIC_MAIL_TYPE: str = field(repr=False, compare=False)
    ELECTRONIC_MAIL_ID: str
    DISCIPLINE_NAME: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    NODE_NAME: Optional[str] = field(default=None, repr=False, compare=False)

    def create_stac_data_provider(self) -> pystac.Provider:
        supplier = pystac.Provider(
            name=self.FULL_NAME, roles=[pystac.ProviderRole.HOST]
        )
        supplier.extra_fields = {
            key.lower(): self.__dict__[key]
            for key in self.__dict__.keys()
            if key is not None and key not in ["FULL_NAME"]
        }
        return supplier


@dataclass(frozen=True, eq=True)
class VolumeModel(AbstractModel):
    DATA_SET_ID: str
    DESCRIPTION: str = field(repr=False, compare=False)
    MEDIUM_TYPE: str = field(repr=False, compare=False)
    PUBLICATION_DATE: str = field(repr=False, compare=False)
    VOLUME_FORMAT: str
    VOLUME_ID: str
    VOLUME_NAME: str
    VOLUME_SERIES_NAME: str
    VOLUME_SET_NAME: str
    VOLUME_SET_ID: str
    VOLUME_VERSION_ID: str
    VOLUMES: str = field(repr=False, compare=False)
    CATALOG: CatalogModel
    DATA_PRODUCER: DataProducerModel
    DIRECTORY: Optional[DirectoryModel] = field(
        default=None, repr=False, compare=False
    )
    FILE: Optional[FileModel] = field(default=None, repr=False, compare=False)
    DATA_SUPPLIER: Optional[DataSupplierModel] = field(
        default=None, repr=False, compare=False
    )
    BLOCK_BYTES: Optional[str] = field(default=None, repr=False, compare=False)
    DATA_SET_COLLECTION_ID: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    FILES: Optional[str] = field(default=None, repr=False, compare=False)
    HARDWARE_MODEL_ID: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    LOGICAL_VOLUMES: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    LOGICAL_VOLUME_PATH_NAME: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    MEDIUM_FORMAT: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    NOTE: Optional[str] = field(default=None, repr=False, compare=False)
    OPERATING_SYSTEM_ID: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    PRODUCT_TYPE: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    TRANSFER_COMMAND_TEXT: Optional[str] = field(
        default=None, repr=False, compare=False
    )
    VOLUME_INSERT_TEXT: Optional[str] = field(
        default=None, repr=False, compare=False
    )

    @classmethod
    def from_dict(cls, env: Dict[str, Any]):
        data = env.copy()

        if "CATALOG" in data:
            data["CATALOG"]: CatalogModel = CatalogModel.from_dict(
                data["CATALOG"]
            )
        if "DATA_PRODUCER" in data:
            data[
                "DATA_PRODUCER"
            ]: DataProducerModel = DataProducerModel.from_dict(
                data["DATA_PRODUCER"]
            )
        if "DATA_SUPPLIER" in data:
            data[
                "DATA_SUPPLIER"
            ]: DataSupplierModel = DataSupplierModel.from_dict(
                data["DATA_SUPPLIER"]
            )
        if "FILE" in data:
            data["FILE"]: FileModel = FileModel.from_dict(data["FILE"])
        if "DIRECTORY" in data:
            data["DIRECTORY"]: DirectoryModel = DirectoryModel.from_dict(
                data["DIRECTORY"]
            )

        parameters = inspect.signature(cls).parameters
        return cls(**{k: v for k, v in data.items() if k in parameters})
