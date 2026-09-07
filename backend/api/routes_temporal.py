"""
Temporal Analysis Route — POST /api/v1/temporal-analysis

Fetches 2021 and 2026 satellite imagery for the same bounding box,
runs detection on both, and computes growth delta metrics.
All values computed live from actual raster data.
"""

import base64
import io
import logging
import uuid

import numpy as np
from PIL import Image
from fastapi import APIRouter, Depends

from backend.auth.firebase_auth import get_current_user, AuthenticatedUser
from backend.database.models import TemporalAnalysisRequest
from backend.database.db import save_temporal_analysis
from backend.services.tile_fetcher import fetch_and_stitch_tiles
from backend.services.detector import (
    get_detector,
    detect_vegetation_contours,
    detect_water_contours,
    detect_built_up_contours,
)
from backend.services.raster_ops import compute_vegetation_percentage
from backend.services.temporal_engine import compute_temporal_diff
from backend.api.routes_analysis import get_scan_store

logger = logging.getLogger("drishti.api.temporal")
router = APIRouter()


def _image_to_base64(image: np.ndarray, max_size: int = 800) -> str:
    """Convert numpy image to base64 JPEG string, resized for transfer."""
    img = Image.fromarray(image)
    # Resize if too large
    if img.width > max_size or img.height > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=75)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@router.post("/temporal-analysis")
async def temporal_analysis(
    request: TemporalAnalysisRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Run temporal analysis comparing requested historical year (Wayback) vs 2026 (current) imagery.
    Reuses existing viewport scan cache when available for super-fast execution.
    """
    min_lat, min_lon, max_lat, max_lon = request.bbox
    zoom = request.zoom
    year = request.year or 2021

    logger.info(
        f"Temporal analysis: [{min_lat:.4f}, {min_lon:.4f}, "
        f"{max_lat:.4f}, {max_lon:.4f}] zoom={zoom} year={year}"
    )

    try:
        # Check scan store cache for current baseline
        scan_store = get_scan_store()
        cached = scan_store.get("latest")
        current_result = None

        if cached and "image" in cached and "transform" in cached:
            c_bounds = cached.get("bounds", {})
            if (
                abs(c_bounds.get("min_lat", 0) - min_lat) < 0.01
                and abs(c_bounds.get("min_lon", 0) - min_lon) < 0.01
            ):
                logger.info("Reusing cached scan result for current baseline")
                current_result = cached

        if current_result is None:
            current_result = await fetch_and_stitch_tiles(
                min_lat, min_lon, max_lat, max_lon, zoom, source="current"
            )

        if current_result is None:
            return {"error": "Failed to fetch current satellite imagery."}

        # Fetch past tiles for requested year
        past_result = await fetch_and_stitch_tiles(
            min_lat, min_lon, max_lat, max_lon, zoom, source="wayback", year=year
        )
        if past_result is None:
            logger.warning(f"Wayback tiles for {year} unavailable, using current raster as baseline.")
            past_result = current_result

        current_image = current_result["image"]
        past_image = past_result["image"]
        current_transform = current_result["transform"]
        past_transform = past_result["transform"]

        detector = get_detector()

        # Check if current layers already computed in cache
        if cached and "layers" in cached and current_result is cached:
            current_detections = cached["layers"].get("detections", {"type": "FeatureCollection", "features": []})
            current_vegetation = cached["layers"].get("vegetation", {"type": "FeatureCollection", "features": []})
            current_water = cached["layers"].get("water", {"type": "FeatureCollection", "features": []})
            current_built = cached["layers"].get("built_up", {"type": "FeatureCollection", "features": []})
        else:
            current_detections = detector.detect(current_image, current_transform)
            current_vegetation = detect_vegetation_contours(current_image, current_transform)
            current_water = detect_water_contours(current_image, current_transform)
            current_built = detect_built_up_contours(current_image, current_transform)

        # Run detection on past imagery
        past_detections = detector.detect(past_image, past_transform)
        past_vegetation = detect_vegetation_contours(past_image, past_transform)
        past_water = detect_water_contours(past_image, past_transform)
        past_built = detect_built_up_contours(past_image, past_transform)

    # Combine features for temporal comparison
    current_all_features = (
        current_detections.get("features", [])
        + current_vegetation.get("features", [])
        + current_water.get("features", [])
        + current_built.get("features", [])
    )
    past_all_features = (
        past_detections.get("features", [])
        + past_vegetation.get("features", [])
        + past_water.get("features", [])
        + past_built.get("features", [])
    )

    current_geojson = {"type": "FeatureCollection", "features": current_all_features}
    past_geojson = {"type": "FeatureCollection", "features": past_all_features}

    # Compute center latitude for GSD calculation
    center_lat = (min_lat + max_lat) / 2.0

    # Compute temporal diff metrics — all live from real data
    growth_metrics = compute_temporal_diff(
        current_geojson=current_geojson,
        past_geojson=past_geojson,
        current_image=current_image,
        past_image=past_image,
        zoom=zoom,
        center_lat=center_lat,
    )

    # Generate scan ID
    scan_id = str(uuid.uuid4())

    # Store in scan store for chat queries
    scan_store = get_scan_store()
    scan_store[scan_id] = {
        "image": current_image,
        "past_image": past_image,
        "transform": current_transform,
        "past_transform": past_transform,
        "bounds": current_result["bounds"],
        "past_bounds": past_result["bounds"],
        "layers": {
            "detections": current_detections,
            "vegetation": current_vegetation,
            "water": current_water,
            "built_up": current_built,
        },
        "past_layers": {
            "detections": past_detections,
            "vegetation": past_vegetation,
            "water": past_water,
            "built_up": past_built,
        },
        "metrics": growth_metrics,
        "zoom": zoom,
        "vegetation_pct": compute_vegetation_percentage(current_image),
        "temporal_metrics": growth_metrics,
    }
    scan_store["latest"] = scan_store[scan_id]

    # Save temporal analysis to database
    growth_metrics["scan_id"] = scan_id
    await save_temporal_analysis(growth_metrics)

    # Generate preview images (base64 for frontend display)
    current_b64 = _image_to_base64(current_image)
    past_b64 = _image_to_base64(past_image)

    logger.info(f"Temporal analysis complete: {scan_id}")

    return {
        "scan_id": scan_id,
            "current_layers": {
                "detections": current_detections,
                "vegetation": current_vegetation,
                "water": current_water,
                "built_up": current_built,
            },
            "past_layers": {
                "detections": past_detections,
                "vegetation": past_vegetation,
                "water": past_water,
                "built_up": past_built,
            },
            "growth_metrics": growth_metrics,
            "current_bounds": current_result["bounds"],
            "past_bounds": past_result["bounds"],
            "current_image_base64": current_b64,
            "past_image_base64": past_b64,
        }
    except Exception as e:
        logger.error(f"Error in temporal_analysis: {e}", exc_info=True)
        return {
            "error": f"Temporal analysis failed: {str(e)}",
            "scan_id": str(uuid.uuid4()),
        }
