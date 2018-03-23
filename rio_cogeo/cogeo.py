"""rio_cogeo.cogeo: translate a file to a cloud optimized geotiff."""

import sys

import click

import numpy

import rasterio
from rasterio.enums import Resampling


def cog_translate(input_file, output_file, profile,
                  indexes=None, nodata=None, alpha=None, overview_level=6):
    """Create Cloud Optimized Geotiff."""
    with rasterio.open(input_file) as src:

        indexes = indexes if indexes else src.indexes

        meta = src.meta
        meta.update(**profile)
        meta['count'] = len(indexes)

        meta.pop('nodata', None)
        meta.pop('alpha', None)

        with rasterio.open(output_file, 'w', **meta) as dst:

            mask = numpy.zeros((dst.height, dst.width), dtype=numpy.uint8)
            wind = list(dst.block_windows(1))

            with click.progressbar(wind, length=len(wind), file=sys.stderr, show_percent=True) as windows:
                for ij, w in windows:
                    matrix = src.read(window=w, indexes=indexes, boundless=True)
                    dst.write(matrix, window=w)

                    if nodata is not None:
                        mask_value = numpy.all(matrix != nodata, axis=0).astype(numpy.uint8) * 255
                    elif alpha is not None:
                        mask_value = src.read(alpha, window=w, boundless=True)
                    else:
                        mask_value = src.read_masks(window=w, indexes=indexes, boundless=True)
                        mask_value = numpy.all(mask_value, axis=0).astype(numpy.uint8) * 255

                    mask[w.row_off:w.row_off + w.height, w.col_off:w.col_off + w.width] = mask_value

            dst.write_mask(mask)

            overviews = [2**j for j in range(1, overview_level + 1)]
            dst.build_overviews(overviews, Resampling.nearest)
            dst.update_tags(ns='rio_overview', resampling=Resampling.nearest.value)
