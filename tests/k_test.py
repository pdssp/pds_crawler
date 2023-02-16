# -*- coding: utf-8 -*-
# import json
# import logging
# from typing import Any
# from typing import Dict
# from typing import Iterator
# from typing import List
# from typing import Optional
# import pystac
# from pds_crawler.extractor import PDSCatalogsDescription
# from pds_crawler.extractor import PdsRecords
# from pds_crawler.extractor import PdsRegistry
# from pds_crawler.load import Database
# from pds_crawler.load import PdsParserFactory
# from pds_crawler.load import StorageCollectionDirectory
# from pds_crawler.models import DataSetModel
# from pds_crawler.models import InstrumentHostModel
# from pds_crawler.models import InstrumentModel
# from pds_crawler.models import MissionModel
# from pds_crawler.models import PdsRecordModel
# from pds_crawler.models import PdsRecordsModel
# from pds_crawler.models import PdsRegistryModel
# from pds_crawler.models import ReferencesModel
# logger = logging.getLogger(__name__)
# class Transform:
#     def __init__(self):
#         self.__missions_dict: Dict[str, pystac.Catalog] = dict()
#     @property
#     def missions_dict(self):
#         return self.__missions_dict
#     def _has_mission(self, catalog: Any):
#         return PdsParserFactory.FileGrammary.MISSION_CATALOG.name in catalog
#     def _has_plateform(self, catalog: Any):
#         return (
#             PdsParserFactory.FileGrammary.INSTRUMENT_HOST_CATALOG.name
#             in catalog
#         )
#     def _has_instrument(self, catalog: Any):
#         return PdsParserFactory.FileGrammary.INSTRUMENT_CATALOG.name in catalog
#     def _has_collection(self, catalog: Any):
#         return PdsParserFactory.FileGrammary.DATA_SET_CATALOG.name in catalog
#     def _is_already_exists(self, mission_id: str, id: str):
#         return (
#             self.missions_dict[mission_id].get_child(id, recursive=True)
#             is not None
#         )
#     def _add_plateforms_to_mission(
#         self,
#         plateforms: List[InstrumentHostModel],
#         mission_id: str,
#         references: Optional[ReferencesModel] = None,
#     ):
#         for plateform in plateforms:
#             self._add_plateform_to_mission(plateform, mission_id, references)
#     def _add_plateform_to_mission(
#         self,
#         plateform: InstrumentHostModel,
#         mission_id: str,
#         references: Optional[ReferencesModel] = None,
#     ):
#         pystac_plateform_cat: pystac.Catalog = plateform.create_stac_catalog(
#             references
#         )
#         if not self._is_already_exists(mission_id, pystac_plateform_cat.id):
#             self.missions_dict[mission_id].add_child(pystac_plateform_cat)
#     def _add_instruments_to_plateform(
#         self,
#         instruments: List[InstrumentModel],
#         mission_id: str,
#         references: Optional[ReferencesModel] = None,
#     ):
#         for instru in instruments:
#             self._add_instrument_to_plateform(instru, mission_id, references)
#     def _add_instrument_to_plateform(
#         self,
#         instrument: InstrumentModel,
#         mission_id: str,
#         references: Optional[ReferencesModel] = None,
#     ):
#         pystac_instru_cat: pystac.Catalog = instrument.create_stac_catalog(
#             references
#         )
#         instrument_id: str = instrument.get_instrument_id()
#         plateform_id: str = instrument.get_plateform_id()
#         if not self._is_already_exists(mission_id, instrument_id):
#             self.missions_dict[mission_id].get_child(
#                 plateform_id, recursive=True
#             ).add_child(pystac_instru_cat)
#     def _add_collections_to_instrument(
#         self,
#         collections: List[DataSetModel],
#         mission_id: str,
#         references: Optional[ReferencesModel] = None,
#     ):
#         for collection in collections:
#             self._add_collection_to_instrument(
#                 collection, mission_id, references
#             )
#     def _add_collection_to_instrument(
#         self,
#         collection: DataSetModel,
#         mission_id: str,
#         references: Optional[ReferencesModel] = None,
#     ):
#         pystac_collection_cat: pystac.Catalog = (
#             collection.create_stac_collection()
#         )
#         collection_id: str = collection.collection_id()
#         instrument_id: str = collection.DATA_SET_HOST.get_instrument_id()
#         if not self._is_already_exists(mission_id, collection_id):
#             self.missions_dict[mission_id].get_child(
#                 instrument_id, recursive=True
#             ).add_child(pystac_collection_cat)
#     def to_stac(self, pds_collections: List[PdsRegistryModel]):
#         catalogs: Iterator[Dict[str, Any]] = pds_ode_catalogs.get_ode_catalogs(
#             pds_collections
#         )
#         for catalog in catalogs:
#             pystac_mission_cat: pystac.Catalog
#             references_ode: ReferencesModel = catalog.get(
#                 PdsParserFactory.FileGrammary.REFERENCE_CATALOG.name
#             )
#             pds_collection: PdsRegistryModel = catalog.get("collection")
#             if self._has_mission(catalog):
#                 mission_ode_cat: MissionModel = catalog[
#                     PdsParserFactory.FileGrammary.MISSION_CATALOG.name
#                 ]
#                 pystac_mission_cat: pystac.Catalog = (
#                     mission_ode_cat.create_stac_catalog(references_ode)
#                 )
#                 if pystac_mission_cat.id not in self.missions_dict:
#                     self.missions_dict[
#                         pystac_mission_cat.id
#                     ] = pystac_mission_cat
#             else:
#                 logger.warning(f"Unable to get mission in {pds_collection}")
#             if self._has_mission(catalog) and self._has_plateform(catalog):
#                 plateform_ode_cat = catalog[
#                     PdsParserFactory.FileGrammary.INSTRUMENT_HOST_CATALOG.name
#                 ]
#                 if isinstance(plateform_ode_cat, list):
#                     self._add_plateforms_to_mission(
#                         plateform_ode_cat,
#                         pystac_mission_cat.id,
#                         references_ode,
#                     )
#                 else:
#                     self._add_plateform_to_mission(
#                         plateform_ode_cat,
#                         pystac_mission_cat.id,
#                         references_ode,
#                     )
#             else:
#                 logger.warning(f"Unable to get plateform in {pds_collection}")
#             if (
#                 self._has_mission(catalog)
#                 and self._has_plateform(catalog)
#                 and self._has_instrument(catalog)
#             ):
#                 instru_ode_cat = catalog[
#                     PdsParserFactory.FileGrammary.INSTRUMENT_CATALOG.name
#                 ]
#                 if isinstance(instru_ode_cat, list):
#                     self._add_instruments_to_plateform(
#                         instru_ode_cat, pystac_mission_cat.id, references_ode
#                     )
#                 else:
#                     self._add_instrument_to_plateform(
#                         instru_ode_cat, pystac_mission_cat.id, references_ode
#                     )
#             else:
#                 logger.warning(f"Unable to get instrument in {pds_collection}")
#             if (
#                 self._has_mission(catalog)
#                 and self._has_plateform(catalog)
#                 and self._has_instrument(catalog)
#                 and self._has_collection(catalog)
#             ):
#                 collection_ode_cat = catalog[
#                     PdsParserFactory.FileGrammary.DATA_SET_CATALOG.name
#                 ]
#                 if isinstance(collection_ode_cat, list):
#                     self._add_collections_to_instrument(
#                         collection_ode_cat,
#                         pystac_mission_cat.id,
#                         references_ode,
#                     )
#                 else:
#                     self._add_collection_to_instrument(
#                         collection_ode_cat,
#                         pystac_mission_cat.id,
#                         references_ode,
#                     )
#             else:
#                 logger.warning(f"Unable to get dataset in {pds_collection}")
#     def describe(self):
#         for mission_key in self.missions_dict.keys():
#             self.missions_dict[mission_key].describe()
#     def save(self, output_file: str):
#         for mission_key in self.missions_dict.keys():
#             pystac_catalog = self.missions_dict[mission_key]
#             pystac_catalog.normalize_hrefs(output_file)
#             pystac_catalog.save()
# if __name__ == "__main__":
#     database = Database("/home/malapert/Work/tmp/data/database/pds.h5")
#     pds_registry = PdsRegistry(database)
#     pds_records = PdsRecords(database)
#     pds_ode_catalogs = PDSCatalogsDescription(database)
#     pds_collections: List[
#         PdsRegistryModel
#     ] = pds_registry.load_pds_collection_from_cache()
#     transform = Transform()
#     transform.to_stac(pds_collections)
#     transform.describe()
#     # transform.save("/tmp/toto")
#     # if PdsParserFactory.FileGrammary.INSTRUMENT_CATALOG.name in catalog:
#     #     instru_ode_cat = catalog[
#     #         PdsParserFactory.FileGrammary.INSTRUMENT_CATALOG.name
#     #     ]
#     #     if isinstance(instru_ode_cat, list):
#     #         for instru in instru_ode_cat:
#     #             if missions_dict[pystac_mission_cat.id].get_child(instru.INSTRUMENT_ID) is None:
#     #                 missions_dict[pystac_mission_cat.id].get_child(
#     #                     f"host:{instru.INSTRUMENT_HOST_ID}", recursive=True
#     #                 ).add_child(instru.create_stac_catalog())
#     #     else:
#     #         if missions_dict[pystac_mission_cat.id].get_child(instru_ode_cat.INSTRUMENT_ID) is None:
#     #             missions_dict[pystac_mission_cat.id].get_child(
#     #                 f"host:{instru_ode_cat.INSTRUMENT_HOST_ID}", recursive=True
#     #             ).add_child(instru_ode_cat.create_stac_catalog())
#     # pystac_mission_catalog.save(pystac.CatalogType.SELF_CONTAINED)
#     # print(json.dumps(pystac_mission_catalog.to_dict(), indent=4))
