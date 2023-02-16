#!/bin/sh
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later

docker build --no-cache=true --build-arg SSH_PRIVATE_KEY="`more ~/.ssh/id_rsa`" -t dev/pds_crawler .
