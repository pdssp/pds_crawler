========
Tutorial
========

Introduction
------------

This section describes tutorials for the use of Python API and the command line.


Python API
-----------

Data extraction
~~~~~~~~~~~~~~~

.. automodule:: pds_crawler.extractor
    :noindex:


Data transformation
~~~~~~~~~~~~~~~~~~~

.. automodule:: pds_crawler.transformer
    :noindex:

ETL API
~~~~~~~

.. automodule:: pds_crawler.etl
    :noindex:

Command line
------------

List of all georeferenced collections available in PDS

.. code:: shell

    pds_crawler extract --type_extract ode_collections

Save a georeferenced collection in the cache

.. code:: shell

    pds_crawler extract --type_extract ode_collections_save --dataset_id CH1-ORB-L-M3-4-L1B-RADIANCE-V1.0

Download ODE records for the cached collection

.. code:: shell

    pds_crawler extract --type_extract ode_records

Download PDS objects for the cached collection

.. code:: shell

    pds_crawler extract --type_extract pds_objects

Transform the downloaded ODE records to items and its parents

.. code:: shell

    pds_crawler transform --type_stac ode_records

Update catalogs and collections from downloaded PDS objects

.. code:: shell

    pds_crawler transform --type_stac pds_objects
