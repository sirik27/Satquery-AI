"""
Tile Fetcher — Downloads live satellite tiles from Esri World Imagery
and Wayback Archive, stitches them into georeferenced in-memory rasters.

All tile math uses standard Slippy Map / Web Mercator conventions.
No mock data — every pixel comes from the actual tile servers.
"""

import io
import math
import hashlib
import logging
from pathlib import Path
from typing import Optional

import httpx
import numpy as np
from PIL import Image

from backend.config import get_settings

logger = logging.getLogger("drishti.tiles")

# Esri World Imagery — current (latest) imagery
ESRI_CURRENT_URL = (
    "https://server.arcgisonline.com/ArcGIS/rest/services/"
    "World_Imagery/MapServer/tile/{z}/{y}/{x}"
)

# Esri Wayback — historical imagery (2021 Wayback archive tile service)
ESRI_WAYBACK_URL = (
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/"
    "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/45009/{z}/{y}/{x}"
)
ESRI_WAYBACK_ALT_URL = (
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/"
    "World_Imagery/MapServer/tile/45009/{z}/{y}/{x}"
)

TILE_SIZE = 256
MAX_TILES_PER_AXIS = 16  # Safety limit to prevent excessive downloads


def lat_lon_to_tile(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert WGS84 lat/lon to Slippy Map tile coordinates."""
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.log(math.tan(lat_rad) + 1.0 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return x, y


def tile_to_lat_lon(x: int, y: int, zoom: int) -> tuple[float, float]:
    """Convert tile coordinates to WGS84 lat/lon (top-left corner of tile)."""
    n = 2.0 ** zoom
    lon = x / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
    lat = math.degrees(lat_rad)
    return lat, lon


def bbox_to_tile_range(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float, zoom: int
) -> tuple[int, int, int, int]:
    """
    Convert a WGS84 bounding box to a range of XYZ tile coordinates.
    Returns (min_x, min_y, max_x, max_y) in tile space.
    """
    # Top-left corner (max_lat, min_lon)
    tl_x, tl_y = lat_lon_to_tile(max_lat, min_lon, zoom)
    # Bottom-right corner (min_lat, max_lon)
    br_x, br_y = lat_lon_to_tile(min_lat, max_lon, zoom)

    # Clamp to safety limits
    width = br_x - tl_x + 1
    height = br_y - tl_y + 1
    if width > MAX_TILES_PER_AXIS or height > MAX_TILES_PER_AXIS:
        logger.warning(
            f"Tile range too large ({width}x{height}), clamping to {MAX_TILES_PER_AXIS}x{MAX_TILES_PER_AXIS}"
        )
        br_x = min(br_x, tl_x + MAX_TILES_PER_AXIS - 1)
        br_y = min(br_y, tl_y + MAX_TILES_PER_AXIS - 1)

    return tl_x, tl_y, br_x, br_y


def _tile_cache_path(x: int, y: int, z: int, source: str) -> Path:
    """Generate a cache file path for a tile."""
    settings = get_settings()
    cache_dir = settings.tile_cache_path / source / str(z) / str(x)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{y}.png"


async def fetch_tile(
    x: int, y: int, z: int, source: str = "current"
) -> Optional[np.ndarray]:
    """
    Fetch a single tile image from Esri servers.
    Uses local disk cache to avoid redundant downloads.
    Returns a numpy RGB array or None if the fetch fails.
    """
    # Check cache first
    cache_file = _tile_cache_path(x, y, z, source)
    if cache_file.exists():
        try:
            img = Image.open(cache_file).convert("RGB")
            return np.array(img)
        except Exception:
            cache_file.unlink(missing_ok=True)

    # Select URL template
    url_template = ESRI_CURRENT_URL if source == "current" else ESRI_WAYBACK_URL
    url = url_template.format(x=x, y=y, z=z)

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                    "Referer": "https://www.arcgis.com/",
                },
            )
            
            # If wayback tile returns 404, fallback to standard Esri tile
            if response.status_code != 200 and source == "past":
                alt_url = ESRI_WAYBACK_ALT_URL.format(x=x, y=y, z=z)
                response = await client.get(
                    alt_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                        "Referer": "https://www.arcgis.com/",
                    },
                )

            response.raise_for_status()

            img = Image.open(io.BytesIO(response.content)).convert("RGB")
            arr = np.array(img)

            # Save to cache
            try:
                img.save(cache_file, format="PNG")
            except Exception as e:
                logger.warning(f"Failed to cache tile {z}/{x}/{y}: {e}")

            return arr

    except httpx.HTTPStatusError as e:
        logger.warning(f"Tile fetch HTTP error {e.response.status_code} for {url}")
        return None
    except Exception as e:
        logger.error(f"Tile fetch error for {z}/{x}/{y}: {e}")
        return None


async def fetch_and_stitch_tiles(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    zoom: int,
    source: str = "current",
) -> Optional[dict]:
    """
    Fetch all tiles covering the bounding box and stitch them into a single image.

    Returns a dict with:
        - 'image': numpy RGB array of the stitched raster
        - 'bounds': actual WGS84 bounds of the stitched area
        - 'transform': affine transform parameters for pixel→WGS84 conversion
        - 'tile_range': (min_x, min_y, max_x, max_y)
        - 'tile_count': total tiles fetched
    """
    min_x, min_y, max_x, max_y = bbox_to_tile_range(
        min_lat, min_lon, max_lat, max_lon, zoom
    )

    cols = max_x - min_x + 1
    rows = max_y - min_y + 1
    total_tiles = cols * rows

    logger.info(
        f"Fetching {total_tiles} tiles ({cols}x{rows}) at zoom {zoom} from {source}"
    )

    # Create empty canvas
    canvas = np.zeros((rows * TILE_SIZE, cols * TILE_SIZE, 3), dtype=np.uint8)
    fetched_count = 0

    for ty in range(min_y, max_y + 1):
        for tx in range(min_x, max_x + 1):
            tile_img = await fetch_tile(tx, ty, zoom, source)
            if tile_img is not None:
                row_offset = (ty - min_y) * TILE_SIZE
                col_offset = (tx - min_x) * TILE_SIZE
                # Handle tiles that might not be exactly TILE_SIZE
                h, w = tile_img.shape[:2]
                h = min(h, TILE_SIZE)
                w = min(w, TILE_SIZE)
                canvas[row_offset : row_offset + h, col_offset : col_offset + w] = (
                    tile_img[:h, :w]
                )
                fetched_count += 1
            else:
                logger.warning(f"Missing tile {zoom}/{tx}/{ty} from {source}")

    if fetched_count == 0:
        logger.error("No tiles fetched — cannot stitch.")
        return None

    # Compute actual bounds of stitched area (tile boundaries, not input bbox)
    tl_lat, tl_lon = tile_to_lat_lon(min_x, min_y, zoom)
    br_lat, br_lon = tile_to_lat_lon(max_x + 1, max_y + 1, zoom)

    actual_bounds = {
        "min_lat": br_lat,
        "min_lon": tl_lon,
        "max_lat": tl_lat,
        "max_lon": br_lon,
    }

    # Compute affine transform: pixel (col, row) → (lon, lat)
    img_h, img_w = canvas.shape[:2]
    lon_per_pixel = (br_lon - tl_lon) / img_w
    lat_per_pixel = (br_lat - tl_lat) / img_h  # Negative because lat decreases downward

    transform = {
        "origin_lon": tl_lon,
        "origin_lat": tl_lat,
        "pixel_width": lon_per_pixel,
        "pixel_height": lat_per_pixel,
        "width": img_w,
        "height": img_h,
    }

    logger.info(
        f"Stitched {fetched_count}/{total_tiles} tiles → "
        f"{img_w}x{img_h}px image covering "
        f"[{actual_bounds['min_lat']:.4f}, {actual_bounds['min_lon']:.4f}] → "
        f"[{actual_bounds['max_lat']:.4f}, {actual_bounds['max_lon']:.4f}]"
    )

    return {
        "image": canvas,
        "bounds": actual_bounds,
        "transform": transform,
        "tile_range": (min_x, min_y, max_x, max_y),
        "tile_count": fetched_count,
        "zoom": zoom,
        "source": source,
    }
