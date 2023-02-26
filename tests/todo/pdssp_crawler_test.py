# -*- coding: utf-8 -*-
import logging

import pytest

import pds_crawler

# import numpy as np
# from PIL import Image

logger = logging.getLogger(__name__)


@pytest.fixture
def setup():
    logger.info("----- Init the tests ------")


def test_init_setup(setup):
    logger.info("Setup is initialized")


# def assert_images_equal(image_1: str, image_2: str):
#     img1 = Image.open(image_1)
#     img2 = Image.open(image_2)

#     # Convert to same mode and size for comparison
#     img2 = img2.convert(img1.mode)
#     img2 = img2.resize(img1.size)

#     diff = np.asarray(img1).astype("float") - np.asarray(img2).astype("float")

#     sum_sq_diff = np.sum(diff ** 2)  # type: ignore

#     if sum_sq_diff == 0:
#         # Images are exactly the same
#         pass
#     else:
#         normalized_sum_sq_diff = sum_sq_diff / np.sqrt(sum_sq_diff)
#         assert normalized_sum_sq_diff < 0.001
