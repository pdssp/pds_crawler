=================
Operations manual
=================

General
-------

*The* :term:`SUM` *shall contain the operational organisation, a reference \
schedule for each operational profile, the list of all the elementary \
operations to be carried out at the site, what to do in order to operate the \
site, the personnel responsible to do it and when.*


Set‐up and initialisation
-------------------------

To install a Python package, you can use pip, a Python package manager that allows
you to download and install packages from PyPI (Python Package Index). First, make
sure that pip is installed on your machine by running in your terminal.

.. code-block:: console

    $ pip --version

If pip is not installed, you can install it using the command on Python versions 3.4
and above.

.. code-block:: console

    $ python -m ensurepip --default-pip

Once pip is installed, you can install a package by running the command

.. code-block:: console

    $ pip install git+https://github.com/pdssp/pds_crawler.git


Getting started
---------------

for PDS crawler capabilities, run the command to display the help:

.. code-block:: console

    $ pds_crawler -h

    usage: pds_crawler [-h] [-v] [--level {INFO,DEBUG,WARNING,ERROR,CRITICAL,TRACE}] [-d DATABASE] {extract,check_extract,transform} ...

    Crawl and extract PDS planetary data from various sources, including a web service and a website, transform the data into the
    SpatioTemporal Asset Catalog (STAC) format.

    positional arguments:
    {extract,check_extract,transform}

    options:
    -h, --help            show this help message and exit
    -v, --version         show program's version number and exit
    --level {INFO,DEBUG,WARNING,ERROR,CRITICAL,TRACE}
                            set Level log (default: INFO)
    -d DATABASE, --database DATABASE
                            Path of the database (default: work/database)

Get PDS collections to retrieve
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To get all georeferenced PDS collections:

.. code-block:: console

    $ pds_crawler extract --type_extract ode_collections

or to get all georeferenced collections from a planet

.. code-block:: console

    $ pds_crawler extract --type_extract ode_collections --planet Mars


Retrieve PDS records from collections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code-block:: console

    $ pds_crawler extract --type_extract ode_records

Retrieve PDS3 objects from collections
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. code-block:: console

    $ pds_crawler extract --type_extract pds_objects

Transform PDS3 object
^^^^^^^^^^^^^^^^^^^^^
.. code-block:: console

    $ pds_crawler transform --type_stac catalog

Transform PDS records
^^^^^^^^^^^^^^^^^^^^^
.. code-block:: console

    $ pds_crawler transform --type_stac records

Mode selection and control
--------------------------

*The* :term:`SUM` *shall give an overview of the access and security features \
of the software that are visible to the user, and in particular:*

* How and from whom to obtain a password
* How to add, delete, or change passwords under user control
* Security and privacy considerations pertaining to the storage and marking of output reports and other media that the user can generate


Normal operations
-----------------

.. uml::

  actor operator as operator
  participant Airflow as airflow
  participant pds_crawler as crawler
  collections "Storage data facility" as storage
  database    "PDSSP Catalog" as pdssp_cat
  database    "PDS data repositories" as pds

  operator -> airflow : Start Extraction & Transformation workflow
  airflow -> crawler : Extract one PDS collection
  crawler -> pds: Extract PDS records from collection
  crawler -> pds: Download JSON responses
  crawler -> storage : Store the JSON responses
  crawler -> storage : Loads one record
  crawler -> crawler : Prepare the PDS3 Objets extraction
  crawler -> pds: Extract the PDS3 Objects from collection
  crawler -> pds : Download the PDS3 objects
  crawler -> storage : Store the PDS3 objects
  crawler -> airflow

  airflow -> crawler : Transform one PDS collection to STAC
  crawler -> storage: load PDS3 objects
  crawler -> storage : create report if error
  crawler -> storage : convert to STAC catalogs and collection

  crawler -> storage: load JSON responses
  crawler -> storage : create report if error
  crawler -> storage : convert to STAC items and if necessary collection and catalogs
  crawler -> airflow
  airflow -> operator

  operator -> storage : consults the report
  operator -> storage : correct or create PDS3 objects

  operator -> airflow : Start update PDS3 objects workflow
  airflow -> crawler : Transform PDS3 objects for one collection
  crawler -> storage: load PDS3 objects
  crawler -> storage : create report if error
  crawler -> storage : convert to STAC catalogs and collection
  crawler -> airflow
  airflow -> operator
  operator -> storage : consults the report
  operator -> storage : check STAC results

  operator -> airflow : Start STAC ingestion workflow
  airflow -> crawler : Ingest STAC repository
  crawler -> pdssp_cat : Ingest STAC repository
  crawler -> airflow
  airflow -> operator


Normal termination
------------------

*The* :term:`SUM` *shall describe how the user can cease or interrupt use of the \
software and how to determine whether normal termination or cessation has \
occurred.*


Error conditions
----------------

*The* :term:`SUM` *shall describe the common error conditions that can occur as a \
result of executing the function, and how to detect that the error has occurred.*


Recover runs
------------

*The* :term:`SUM` *shall include the detailed procedures for restart or recovery \
from errors or malfunctions occurring during processing and for ensuring \
continuity of operations in the event of emergencies.*
