#!/bin/sh
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
set search
set ps

search=`docker images | grep dev/pds_crawler | wc -l`
if [ $search = 0 ];
then
	# only the heaader - no image found
	echo "Please build the image by running 'make docker-container-dev'"
	exit 1
fi

ps=`docker ps -a | grep develop-pds_crawler | wc -l`
if [ $ps = 0 ];
then
	echo "no container available, start one"
	docker run --name=develop-pds_crawler #\
		#-v /dev:/dev \
		#-v `echo ~`:/home/${USER} \
		#-v `pwd`/data:/srv/pds_crawler/data \
		#-p 8082:8082 \
		-it dev/pds_crawler /bin/bash
	exit $?
fi

ps=`docker ps | grep develop-pds_crawler | wc -l`
if [ $ps = 0 ];
then
	echo "container available but not started, start and go inside"
	docker start develop-pds_crawler
	docker exec -it develop-pds_crawler /bin/bash
else
	echo "container started, go inside"
	docker exec -it develop-pds_crawler /bin/bash
fi
