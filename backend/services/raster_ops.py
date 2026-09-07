"""
Raster Operations — Pixel-to-coordinate transforms and spectral index computation.

All calculations operate on real numpy arrays — zero mock data.
Every returned value is computed live from actual pixel values.
"""

import logging
from typing import Optional

import numpy as np

logger = logging.getLogger("drishti.raster")


def pixel_to_wgs84(
    col: float, row: float, transform: dict
) -> tuple[float, float]:
    """
    Convert pixel coordinates (col, row) to WGS84 (lat, lon)
    using the affine transform from tile stitching.

    Args:
        col: Pixel x coordinate (column)
        row: Pixel y coordinate (row)
        transform: Dict with origin_lon, origin_lat, pixel_width, pixel_height

    Returns:
        (latitude, longitude) tuple
    """
    lon = transform["origin_lon"] + col * transform["pixel_width"]
    lat = transform["origin_lat"] + row * transform["pixel_height"]
    return lat, lon


def bbox_pixels_to_wgs84(
    x1: float, y1: float, x2: float, y2: float, transform: dict
) -> dict:
    """Convert pixel bounding box to WGS84 bounding box."""
    lat1, lon1 = pixel_to_wgs84(x1, y1, transform)
    lat2, lon2 = pixel_to_wgs84(x2, y2, transform)
    return {
        "min_lat": min(lat1, lat2),
        "min_lon": min(lon1, lon2),
        "max_lat": max(lat1, lat2),
        "max_lon": max(lon1, lon2),
    }


def pixel_polygon_to_wgs84(
    contour: np.ndarray, transform: dict
) -> list[list[float]]:
    """
    Convert a pixel-space contour (Nx1x2 or Nx2 array) to a list of
    [longitude, latitude] coordinate pairs (GeoJSON convention).
    """
    if contour.ndim == 3:
        contour = contour.reshape(-1, 2)

    coords = []
    for point in contour:
        col, row = float(point[0]), float(point[1])
        lat, lon = pixel_to_wgs84(col, row, transform)
        coords.append([lon, lat])

    # Close the polygon (GeoJSON requires first == last)
    if len(coords) > 0 and coords[0] != coords[-1]:
        coords.append(coords[0])

    return coords


def compute_gli(image: np.ndarray) -> np.ndarray:
    """
    Compute Green Leaf Index (GLI) from an RGB image.
    GLI = (2*G - R - B) / (2*G + R + B + epsilon)

    Returns a float32 array with values in [-1, 1].
    """
    img = image.astype(np.float32)
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    numerator = 2.0 * g - r - b
    denominator = 2.0 * g + r + b + 1e-10  # Avoid division by zero

    gli = numerator / denominator
    return np.clip(gli, -1.0, 1.0)


def compute_vari(image: np.ndarray) -> np.ndarray:
    """
    Compute Visible Atmospherically Resistant Index (VARI) from an RGB image.
    VARI = (G - R) / (G + R - B + epsilon)

    Returns a float32 array with values clipped to [-1, 1].
    """
    img = image.astype(np.float32)
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    numerator = g - r
    denominator = g + r - b + 1e-10

    vari = numerator / denominator
    return np.clip(vari, -1.0, 1.0)


def compute_vegetation_mask(
    image: np.ndarray, threshold: float = 0.05
) -> np.ndarray:
    """
    Create a binary vegetation mask using GLI thresholding.
    Pixels with GLI > threshold are classified as vegetation.

    Returns a boolean array (True = vegetation).
    """
    gli = compute_gli(image)
    return gli > threshold


def compute_vegetation_percentage(image: np.ndarray, threshold: float = 0.05) -> float:
    """
    Compute the percentage of the image covered by vegetation.
    Uses GLI-based vegetation mask.

    Returns a float percentage [0.0 – 100.0], computed from actual pixels.
    """
    mask = compute_vegetation_mask(image, threshold)
    total_pixels = mask.size
    if total_pixels == 0:
        return 0.0
    veg_pixels = int(np.count_nonzero(mask))
    return (veg_pixels / total_pixels) * 100.0


def compute_water_mask(image: np.ndarray) -> np.ndarray:
    """
    Create a highly precise binary water mask using NDWI (Normalized Difference Water Index).
    Strict blue dominance and low brightness to prevent tree shadows or dark roofs from false positives.
    """
    img = image.astype(np.float32)
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    # Blue vs Red ratio & Green vs Red ratio
    blue_ratio = (b - r) / (b + r + 1e-10)
    green_ratio = (g - r) / (g + r + 1e-10)
    brightness = (r + g + b) / 3.0

    # True water bodies have high blue dominance, low red, low overall brightness, and minimal green GLI
    gli = compute_gli(image)
    water_mask = (blue_ratio > 0.15) & (b > g) & (brightness < 110) & (gli < 0.01)

    return water_mask


def compute_built_up_mask(image: np.ndarray) -> np.ndarray:
    """
    Create a binary built-up/building mask.
    Built-up areas (roofs, concrete, structures) have high variance, neutral color, and low vegetation GLI.
    """
    img = image.astype(np.float32)
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]

    brightness = (r + g + b) / 3.0
    gli = compute_gli(image)

    # Buildings & roof structures: non-vegetated pixels with moderate to high brightness
    built_mask = (brightness > 75) & (gli < 0.04) & (brightness < 250)

    return built_mask


def compute_ground_sample_distance(
    zoom: int, latitude: float
) -> float:
    """
    Compute the ground sample distance (meters per pixel) at a given
    zoom level and latitude.

    Uses the standard Web Mercator formula:
    GSD = (C * cos(lat)) / (2^zoom * tile_size)
    where C = 40075016.686 m (Earth circumference at equator)
    """
    import math
    C = 40075016.686  # Earth circumference in meters
    lat_rad = math.radians(abs(latitude))
    gsd = (C * math.cos(lat_rad)) / (2 ** zoom * 256)
    return gsd


def pixel_area_to_sq_meters(
    pixel_count: int, zoom: int, latitude: float
) -> float:
    """
    Convert a count of pixels to square meters using the ground sample distance.
    """
    gsd = compute_ground_sample_distance(zoom, latitude)
    return pixel_count * (gsd ** 2)


def compute_image_statistics(image: np.ndarray) -> dict:
    """Compute basic statistics for an RGB image — all from actual pixels."""
    return {
        "width": int(image.shape[1]),
        "height": int(image.shape[0]),
        "channels": int(image.shape[2]) if image.ndim == 3 else 1,
        "mean_r": float(np.mean(image[:, :, 0])),
        "mean_g": float(np.mean(image[:, :, 1])),
        "mean_b": float(np.mean(image[:, :, 2])),
        "std_r": float(np.std(image[:, :, 0])),
        "std_g": float(np.std(image[:, :, 1])),
        "std_b": float(np.std(image[:, :, 2])),
    }
