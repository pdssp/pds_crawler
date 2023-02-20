# -*- coding: utf-8 -*-
# pds-crawler - ETL to index PDS data to pdssp
# Copyright (C) 2023 - CNES (Jean-Christophe Malapert for Pôle Surfaces Planétaires)
# This file is part of pds-crawler <https://github.com/pdssp/pds_crawler>
# SPDX-License-Identifier: LGPL-3.0-or-later
"""
Module Name:
    strategy

Description:
    the pds_to_stac provides a storage strategy for storing data with "id" with ":" and to avoid
    a large number of items in one single directory.

Classes:
    LargeDataVolumeStrategy:
        Specific strategy

Author:
    Jean-Christophe Malapert
"""
import os
from typing import Callable
from typing import List

import pystac
from pystac.layout import CustomLayoutStrategy
from pystac.utils import join_path_or_url
from pystac.utils import JoinType


class LargeDataVolumeStrategy:
    def __init__(self) -> None:
        pass

    def _remove_filename_if_needed(
        self, parent_dir: str, filename: str
    ) -> str:
        if filename in parent_dir:
            parent_dir = parent_dir.replace(filename, "")
        return parent_dir

    def _fix_parent_directory(self, parent_dir: str) -> str:
        if "urn:" in parent_dir:
            parent_dir = (
                parent_dir[:-1] if parent_dir[-1] == "/" else parent_dir
            )
            paths: List[str] = parent_dir.split("/")
            base = paths[:-1]
            directory = paths[-1].split(":")[-1]
            parent_dir = os.path.join("/".join(base), directory)
        return parent_dir

    def _hash_storage(self, key, base_path):
        # Use the Python hash to generate an unique integer for the key
        hashed_key = hash(key)

        # Calculate the directory index using the modulo and the number of directories
        num_dirs = 1000  # Number of directories
        dir_index = hashed_key % num_dirs
        return str(dir_index)

    def get_strategy(self) -> CustomLayoutStrategy:
        """Creates a strategy to define the directories name in STAC catalog and childrens

        Returns:
            CustomLayoutStrategy: A custom strategy for the name of the directories
        """

        def get_custom_catalog_func() -> (
            Callable[[pystac.Catalog, str, bool], str]
        ):
            def fn(col: pystac.Catalog, parent_dir: str, is_root: bool) -> str:
                parent_dir = self._remove_filename_if_needed(
                    parent_dir, "catalog.json"
                )
                path: str
                if is_root:
                    # need to fix the parent_directory when root
                    parent_dir = self._fix_parent_directory(parent_dir)
                    path = join_path_or_url(
                        JoinType.URL, parent_dir, "catalog.json"
                    )
                else:
                    new_id = col.id.split(":")[-1]
                    path = join_path_or_url(
                        JoinType.URL, parent_dir, new_id, "catalog.json"
                    )
                return path

            return fn

        def get_custom_collection_func() -> (
            Callable[[pystac.Collection, str, bool], str]
        ):
            def fn(
                col: pystac.Collection, parent_dir: str, is_root: bool
            ) -> str:
                parent_dir = self._remove_filename_if_needed(
                    parent_dir, "collection.json"
                )
                path: str
                if is_root:
                    parent_dir = self._fix_parent_directory(parent_dir)
                    path = join_path_or_url(
                        JoinType.URL, parent_dir, "collection.json"
                    )
                else:
                    new_id = col.id.split(":")[-1]
                    path = join_path_or_url(
                        JoinType.URL, parent_dir, new_id, "collection.json"
                    )
                return path

            return fn

        def get_custom_item_func() -> Callable[[pystac.Item, str], str]:
            def fn(item: pystac.Item, parent_dir: str) -> str:
                dir_index: str = self._hash_storage(item.id, parent_dir)
                path = join_path_or_url(
                    JoinType.URL,
                    parent_dir,
                    dir_index,
                    ".".join((str(item.id), "json")),
                )
                return path

            return fn

        strategy = CustomLayoutStrategy(
            catalog_func=get_custom_catalog_func(),
            collection_func=get_custom_collection_func(),
            item_func=get_custom_item_func(),
        )

        return strategy
