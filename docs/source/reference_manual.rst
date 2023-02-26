================
Reference manual
================

Introduction
============

This section is the reference manual of the Python API.


Extraction
==========

Introduction
------------

.. automodule:: pds_crawler.extractor

Module for extracting records and collections from ODE web service
------------------------------------------------------------------

.. automodule:: pds_crawler.extractor.pds_ode_ws

Searching for collections
~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: PdsRegistry
   :members:
   :private-members:

Searching for records in a given collection
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: PdsRecords
   :members:
   :private-members:

Module for extracting PDS3 objects from the ODE archive
-------------------------------------------------------

.. automodule:: pds_crawler.extractor.pds_ode_website

Extracting URLs of PDS3 objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: Crawler
   :members:
   :private-members:

Extracting PDS3 objects
~~~~~~~~~~~~~~~~~~~~~~~

.. autoclass:: PDSCatalogDescription
   :members:
   :private-members:

.. autoclass:: PDSCatalogsDescription
   :members:
   :private-members:

Transformation
==============

Introduction
------------

.. automodule:: pds_crawler.transformer

Module for STAC stransformation
--------------------------------

.. automodule:: pds_crawler.transformer.pds_to_stac

.. autoclass:: StacTransformer
   :members:
   :private-members:

.. autoclass:: StacRecordsTransformer
   :members:
   :private-members:

.. autoclass:: StacCatalogTransformer
   :members:
   :private-members:

Load
====

Introduction
------------

.. automodule:: pds_crawler.load

Storage module
---------------

.. automodule:: pds_crawler.load.database

.. autoclass:: StacStorage
   :members:
   :private-members:

.. autoclass:: PdsCollectionStorage
   :members:
   :private-members:

.. autoclass:: PdsStorage
   :members:
   :private-members:

.. autoclass:: Hdf5Storage
   :members:
   :private-members:

.. autoclass:: Database
   :members:
   :private-members:

Parsing PDS3 objects module
---------------------------

.. automodule:: pds_crawler.load.pds_objects_parser

.. autoclass:: GrammarEnum
   :members:
   :private-members:

.. autoclass:: PdsTransformer
   :members:
   :private-members:

.. autoclass:: ProjectionDescriptionTransformer
   :members:
   :private-members:

.. autoclass:: MissionCatalogTransformer
   :members:
   :private-members:

.. autoclass:: ReferenceCatalogTransformer
   :members:
   :private-members:

.. autoclass:: PersonCatalogTransformer
   :members:
   :private-members:

.. autoclass:: VolumeDescriptionTransformer
   :members:
   :private-members:

.. autoclass:: InstrumentCatalogTransformer
   :members:
   :private-members:

.. autoclass:: InstrumentHostCatalogTransformer
   :members:
   :private-members:

.. autoclass:: DataSetCatalogTransformer
   :members:
   :private-members:

.. autoclass:: PdsParserFactory
   :members:
   :private-members:

Strategy module
---------------

.. automodule:: pds_crawler.load.strategy

.. autoclass:: LargeDataVolumeStrategy
   :members:
   :private-members:

Models
======

Introduction
------------

.. automodule:: pds_crawler.models

common module
-------------

.. automodule:: pds_crawler.models.common

.. autoclass:: AbstractModel
   :members:
   :private-members:

Module describing the models of ODE webservice
----------------------------------------------

.. automodule:: pds_crawler.models.ode_ws_models
   :noindex:

.. autoclass:: ProductFile
   :noindex:
   :members:
   :private-members:

.. autoclass:: PdsRegistryModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: PdsRecordModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: PdsRecordsModel
   :noindex:
   :members:
   :private-members:

Module describing the models of PDS3 objects
--------------------------------------------

.. automodule:: pds_crawler.models.pds_models
   :noindex:

.. autoclass:: ReferenceModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: ReferencesModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSetInformationModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSetTargetModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSetHostModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSetMissionModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSetReferenceInformationModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSetModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: InstrumentReferenceInfoModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: InstrumentInformationModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: InstrumentModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: InstrumentHostInformationModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: InstrumentHostReferenceInfoModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: InstrumentHostModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: MissionInformationModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: MissionTargetModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: MissionHostModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: MissionReferenceInformationModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSetMapProjectionRefInfoModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSetMapProjectionInfoModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSetMapProjectionModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: MissionModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: PersonnelInformationModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: PersonnelElectronicMailModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: PersonnelModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: CatalogModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataProducerModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: FileModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DirectoryModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: DataSupplierModel
   :noindex:
   :members:
   :private-members:

.. autoclass:: VolumeModel
   :noindex:
   :members:
   :private-members:
