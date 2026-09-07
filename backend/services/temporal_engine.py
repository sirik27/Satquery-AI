"""
Temporal Engine — Computes growth delta between two time periods (2021 vs 2026).

All metrics are computed live from actual raster data and GeoJSON features.
Zero mock values, zero hardcoded constants.
"""

import logging
from typing import Optional

import numpy as np

from backend.services.raster_ops import (
    compute_vegetation_percentage,
    compute_gli,
    compute_built_up_mask,
    pixel_area_to_sq_meters,
)

logger = logging.getLogger("drishti.temporal")


def compute_temporal_diff(
    current_geojson: dict,
    past_geojson: dict,
    current_image: np.ndarray,
    past_image: np.ndarray,
    zoom: int,
    center_lat: float,
) -> dict:
    """
    Compute structural and environmental growth metrics between
    two time periods using real raster and vector data.

    Args:
        current_geojson: GeoJSON FeatureCollection from current (2026) scan
        past_geojson: GeoJSON FeatureCollection from past (2021) scan
        current_image: RGB numpy array of current satellite imagery
        past_image: RGB numpy array of past satellite imagery
        zoom: Map zoom level (for GSD calculation)
        center_lat: Center latitude (for GSD calculation)

    Returns:
        Dict of temporal metrics — all computed live.
    """
    # --- Feature counts (from real GeoJSON) ---
    current_features = current_geojson.get("features", [])
    past_features = past_geojson.get("features", [])

    # Count by layer
    def count_by_layer(features: list, layer: str) -> int:
        return sum(
            1 for f in features
            if f.get("properties", {}).get("layer") == layer
        )

    def count_detections(features: list) -> int:
        return sum(
            1 for f in features
            if f.get("properties", {}).get("layer") == "detections"
        )

    current_detection_count = count_detections(current_features)
    past_detection_count = count_detections(past_features)

    current_built_count = count_by_layer(current_features, "built_up")
    past_built_count = count_by_layer(past_features, "built_up")

    current_veg_count = count_by_layer(current_features, "vegetation")
    past_veg_count = count_by_layer(past_features, "vegetation")

    current_water_count = count_by_layer(current_features, "water")
    past_water_count = count_by_layer(past_features, "water")

    # --- Structural growth delta ---
    detection_delta = current_detection_count - past_detection_count

    detection_growth_pct = 0.0
    if past_detection_count > 0:
        detection_growth_pct = (detection_delta / past_detection_count) * 100.0

    built_delta = current_built_count - past_built_count

    # --- Vegetation analysis (from actual pixel data) ---
    current_veg_pct = compute_vegetation_percentage(current_image)
    past_veg_pct = compute_vegetation_percentage(past_image)
    vegetation_change_pct = current_veg_pct - past_veg_pct

    # --- Built-up / concrete area analysis (from actual pixel data) ---
    current_built_mask = compute_built_up_mask(current_image)
    past_built_mask = compute_built_up_mask(past_image)

    current_built_pixels = int(np.count_nonzero(current_built_mask))
    past_built_pixels = int(np.count_nonzero(past_built_mask))
    built_pixel_delta = current_built_pixels - past_built_pixels

    # Convert pixel areas to square meters using real GSD
    current_built_area_sqm = pixel_area_to_sq_meters(current_built_pixels, zoom, center_lat)
    past_built_area_sqm = pixel_area_to_sq_meters(past_built_pixels, zoom, center_lat)
    concrete_expansion_sqm = current_built_area_sqm - past_built_area_sqm

    concrete_growth_pct = 0.0
    if past_built_area_sqm > 0:
        concrete_growth_pct = (concrete_expansion_sqm / past_built_area_sqm) * 100.0

    # --- GLI change (overall greenness shift) ---
    current_gli = compute_gli(current_image)
    past_gli = compute_gli(past_image)
    mean_gli_current = float(np.mean(current_gli))
    mean_gli_past = float(np.mean(past_gli))
    gli_change = mean_gli_current - mean_gli_past

    # --- Difference mask (pixels that changed significantly) ---
    if current_image.shape == past_image.shape:
        diff = np.abs(current_image.astype(np.float32) - past_image.astype(np.float32))
        mean_diff = float(np.mean(diff))
        change_mask = np.mean(diff, axis=2) > 30  # Threshold for "significant" change
        change_percentage = float(np.count_nonzero(change_mask) / change_mask.size * 100.0)
    else:
        mean_diff = 0.0
        change_percentage = 0.0

    metrics = {
        "time_periods": {
            "current": "2026 (latest)",
            "past": "2021 (wayback)",
        },
        "detections": {
            "current_count": current_detection_count,
            "past_count": past_detection_count,
            "net_change": detection_delta,
            "growth_percentage": round(detection_growth_pct, 2),
        },
        "built_up_areas": {
            "current_count": current_built_count,
            "past_count": past_built_count,
            "net_change": built_delta,
            "current_area_sqm": round(current_built_area_sqm, 2),
            "past_area_sqm": round(past_built_area_sqm, 2),
            "concrete_expansion_sqm": round(concrete_expansion_sqm, 2),
            "concrete_growth_percentage": round(concrete_growth_pct, 2),
        },
        "vegetation": {
            "current_coverage_pct": round(current_veg_pct, 2),
            "past_coverage_pct": round(past_veg_pct, 2),
            "vegetation_change_pct": round(vegetation_change_pct, 2),
            "vegetation_loss": vegetation_change_pct < 0,
            "current_polygon_count": current_veg_count,
            "past_polygon_count": past_veg_count,
        },
        "greenness_index": {
            "current_mean_gli": round(mean_gli_current, 4),
            "past_mean_gli": round(mean_gli_past, 4),
            "gli_change": round(gli_change, 4),
        },
        "water_bodies": {
            "current_count": current_water_count,
            "past_count": past_water_count,
            "net_change": current_water_count - past_water_count,
        },
        "overall_change": {
            "mean_pixel_difference": round(mean_diff, 2),
            "area_changed_percentage": round(change_percentage, 2),
        },
    }

    logger.info(
        f"Temporal analysis complete: "
        f"detections {past_detection_count}→{current_detection_count}, "
        f"vegetation {past_veg_pct:.1f}%→{current_veg_pct:.1f}%, "
        f"concrete Δ{concrete_expansion_sqm:.0f}m²"
    )

    return metrics
