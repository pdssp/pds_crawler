#############################
External view of the software
#############################

*******
General
*******

This section describes the interactions of PDS crawler with external interfaces on
the :term:`PDSSP` infrastructure. The different interfaces are the following:

- the platform where the PDS crawler is hosted
- the :term:`PDS` as data source
- the airflow software that allow the operator to pilot the PDS crawler

.. image:: https://pdssp.github.io/pdssp-docs/_images/pdssp_architecture.png
  :width: 800
  :alt: the PDSSP infrastructure

**********
Interfaces
**********

PDSSP Plateform
===============
The plateform must be a computer with Linux system where the following components must be installed :

- a browser to operate Airflow
- docker

The platform must have xxx GB of disk space for data and xxx for images and containers

Data files
==========

PDS3 Objects
------------

.. automodule:: pds_crawler.models.pds_models


ODE web services
----------------

.. automodule:: pds_crawler.models.ode_ws_models
