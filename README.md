# pds-crawler

![image](https://img.shields.io/github/v/tag/pdssp/pds_crawler)

![image](https://img.shields.io/github/v/release/pdssp/pds_crawler?include_prereleases)

[![image](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/pdssp/pds_crawler/graphs/commit-activity)

ETL to index PDS data to pdssp

```mermaid 
graph TD     
  A[PDS ODE Web Service - collection] --> |JSON| D(Extraction)     
  B[PDS ODE Web Service - records] --> |JSON| E(Extraction)     
  C[PDS ODE Web Site] --> |REFERENCE_CATALOG, MISSION_CATALOG,<br>PERSONNEL_CATALOG, INSTRUMENT_CATALOG,<br>INSTRUMENT_HOST_CATALOG,DATA_SET_CATALOG,<br>VOL_DESC, DATA_SET_MAP_PROJECTION_CATALOG| F(Extraction)     
  E(Extraction) --> |Files| H[Storage File System]     
  F(Extraction) --> |Files| M[Storage File System]     
  D(Extraction) --> |JSON PdsRegistryModel| I[HDF5]     
  I[HDF5] --> |PdsRegistryModel| N[Transform]     
  M[Storage File System] --> |PdsRecordsModel, DataSetMapProjectionModel,<br>MissionModel, ReferencesModel,<br>PersonnelsModel, VolumeModel,<br>InstrumentModel, InstrumentHostModel,<br>DataSetModel| L[Transform]     
  H[Storage File System] --> |PdsRecordModel| N[Transform]     
  I[HDF5] --> |PdsRegistryModel| L[Transform]     
  N[Transform] --> |STAC Item, STAC Collection, STAC Catalog| O[STAC repository]     
  L[Transform] --> |STAC Collection, STAC Catalog| O[STAC repository] 
  ```

## Stable release

To install pds-crawler, run this command in your terminal:

``` console
$ pip install pds_crawler
```

This is the preferred method to install pds-crawler, as it will always
install the most recent stable release.

If you don\'t have [pip](https://pip.pypa.io) installed, this [Python
installation
guide](http://docs.python-guide.org/en/latest/starting/installation/)
can guide you through the process.

## From sources

The sources for pds-crawler can be downloaded from the [Github
repo](https://github.com/pdssp/pds_crawler).

You can either clone the public repository:

``` console
$ git clone git://github.com/pdssp/pds_crawler
```

Or download the
[tarball](https://github.com/pdssp/pds_crawler/tarball/master):

``` console
$ curl -OJL https://github.com/pdssp/pds_crawler/tarball/master
```

Once you have a copy of the source, you can install it with:

``` console
$ make  # install in the system root
$ make user # or Install for non-root usage
```

## Development

``` console
$ git clone https://github.com/pdssp/pds_crawler
$ cd pds_crawler
$ make prepare-dev
$ source .pds_crawler
$ make install-dev
```

To get more information about the preconfigured tasks:

``` console
$ make help
```

## Usage

To use pds-crawler in a project:

``` shell
import pds_crawler
```

## Run tests

``` console
$make tests
```

## Author

👤 **Jean-Christophe Malapert**

## 🤝 Contributing

Contributions, issues and feature requests are welcome!\<br /\>Feel free
to check \[issues page\](<https://github.com/pdssp/pds_crawler/issues>).
You can also take a look at the \[contributing
guide\](<https://github.com/pdssp/pds_crawler/blob/master/CONTRIBUTING.rst>)

## 📝 License

This project is \[GNU Lesser General Public License
v3\](<https://github.com/pdssp/pds_crawler/blob/master/LICENSE>)
licensed.
