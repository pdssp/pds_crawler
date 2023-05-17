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
        Specific strategy for organizing the STAC catalogs and items.

.. uml::

    class LargeDataVolumeStrategy {
        - _remove_filename_if_needed(parent_dir: str, filename: str) -> str
        - _fix_parent_directory(parent_dir: str) -> str
        - _hash_storage(key, base_path) -> str
        + get_strategy() -> CustomLayoutStrategy
    }
    class CustomLayoutStrategy {
        + catalog_func
        + collection_func
        + item_func
        + __init__(catalog_func, collection_func, item_func)
    }
    LargeDataVolumeStrategy --> CustomLayoutStrategy

Author:
    Jean-Christophe Malapert
"""
import logging
import os
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import TYPE_CHECKING

import numpy as np
import pystac
from pystac import STACError
from pystac.layout import CustomLayoutStrategy
from pystac.link import HREF
from pystac.stac_io import DefaultStacIO
from pystac.utils import join_path_or_url
from pystac.utils import JoinType

try:
    import orjson
except ImportError:
    orjson = None  # type: ignore[assignment]
    import json

logger = logging.getLogger(__file__)


class LargeDataVolumeStrategy:
    """Custom layout strategy for organizing the STAC catalogs and items for large items
    in a collection."""

    def __init__(self) -> None:
        pass

    def _remove_filename_if_needed(
        self, parent_dir: str, filename: str
    ) -> str:
        if filename in parent_dir:
            parent_dir = parent_dir.replace(filename, "")
        return parent_dir

    def _fix_parent_directory(self, parent_dir: str) -> str:
        if "urn:" not in parent_dir:
            return parent_dir

        parent_dir = parent_dir.rstrip("/")
        base_path, directory_name = parent_dir.rsplit("/", 1)
        directory_name = directory_name.split(":")[-1]
        return f"{base_path}/{directory_name}"

    def _hash_storage(self, key, num_dirs=1000):
        # Use the Python hash to generate an unique integer for the key
        hashed_key = hash(key)

        # Calculate the directory index using the modulo and the number of directories
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
                    path = f"{parent_dir}/catalog.json"
                else:
                    new_id = str(col.id).split(":")[-1]
                    path = f"{parent_dir}/{new_id}/catalog.json"
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
                    path = f"{parent_dir}/collection.json"
                else:
                    new_id = col.id.split(":")[-1]
                    path = f"{parent_dir}/{new_id}/collection.json"
                return path

            return fn

        def get_custom_item_func() -> Callable[[pystac.Item, str], str]:
            def fn(item: pystac.Item, parent_dir: str) -> str:
                dir_index: str = self._hash_storage(item.id)
                path = f"{parent_dir}/{dir_index}/{item.id}.json"
                return path

            return fn

        strategy = CustomLayoutStrategy(
            catalog_func=get_custom_catalog_func(),
            collection_func=get_custom_collection_func(),
            item_func=get_custom_item_func(),
        )

        return strategy


class PdsspStacIO(DefaultStacIO):
    def write_text_to_href(self, href: str, txt: str) -> None:
        """Writes text to file using UTF-8 encoding.

        This implementation uses :func:`open` and therefore can only write to the local
        file system.

        Args:

            href : The path to which the file will be written.
            txt : The string content to write to the file.
        """
        href = os.fspath(href)
        dirname = os.path.dirname(href)
        if dirname != "" and not os.path.isdir(dirname):
            os.makedirs(dirname, exist_ok=True)
        with open(href, "w", encoding="utf-8") as f:
            f.write(txt)

    def json_dumps(
        self, json_dict: Dict[str, Any], *args: Any, **kwargs: Any
    ) -> str:
        """Method used internally by :class:`StacIO` instances to serialize a dictionary
        to a JSON string.

        This method may be overwritten in :class:`StacIO` sub-classes to provide custom
        serialization logic. The method accepts arbitrary keyword arguments. These are
        not used by the default implementation, but may be used by sub-class
        implementations.

        Args:
            json_dict : The dictionary to serialize
        """
        if orjson is not None:
            # Convertir tous les objets numpy.float64 en objets float natifs
            try:
                return orjson.dumps(
                    json_dict, option=orjson.OPT_INDENT_2, **kwargs
                ).decode("utf-8")
            except TypeError as error:
                logger.error(
                    f"""--- Error ---
                {json_dict}
                """
                )
                logger.error("Detail of the error")
                toto = json_dict["properties"]
                for k, v in toto.items():
                    if isinstance(v, list):
                        for a in v:
                            logger.error(f"{a} - {type(a)}")
                    elif isinstance(v, dict):
                        for a, b in dict.items():
                            logger.error(f"{a} = {b} - {type(b)}")
                    else:
                        logger.error(f"{k} = {v} - {type(v)}")
                raise error
        else:
            return json.dumps(json_dict, *args, indent=2, **kwargs)

    def save_json(
        self,
        dest: HREF,
        json_dict: Dict[str, Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Write a dict to the given URI as JSON.

        See :func:`StacIO.write_text <pystac.StacIO.write_text>` for usage of
        str vs Link as a parameter.

        Args:
            dest : The destination file to write the text to.
            json_dict : The JSON dict to write.
            *args : Additional positional arguments to be passed to
                :meth:`StacIO.json_dumps`.
            **kwargs : Additional keyword arguments to be passed to
                :meth:`StacIO.json_dumps`.
        """
        txt = self.json_dumps(json_dict, *args, **kwargs)
        self.write_text(dest, txt)

    def save_object(
        self,
        include_self_link: bool = True,
        dest_href: Optional[str] = None,
        stac_io: Optional[pystac.StacIO] = None,
    ) -> None:
        """Saves this STAC Object to it's 'self' HREF.

        Args:
            include_self_link : If this is true, include the 'self' link with
                this object. Otherwise, leave out the self link.
            dest_href : Optional HREF to save the file to. If None, the object
                will be saved to the object's self href.
            stac_io: Optional instance of StacIO to use. If not provided, will use the
                instance set on the object's root if available, otherwise will use the
                default instance.

        Raises:
            :class:`~pystac.STACError`: If no self href is set, this error will be
            raised.

        Note:
            When to include a self link is described in the :stac-spec:`Use of Links
            section of the STAC best practices document
            <best-practices.md#use-of-links>`
        """
        if stac_io is None:
            root = self.get_root()
            if root is not None:
                root_stac_io = root._stac_io
                if root_stac_io is not None:
                    stac_io = root_stac_io

            if stac_io is None:
                stac_io = pystac.StacIO.default()

        if dest_href is None:
            self_href = self.get_self_href()
            if self_href is None:
                raise STACError(
                    "Self HREF must be set before saving without an explicit dest_href."
                )
            dest_href = self_href

        stac_io.save_json(
            dest_href, self.to_dict(include_self_link=include_self_link)
        )
