"""
Viewport Scan Route — POST /api/v1/scan-viewport

Orchestrates: tile fetch → stitch → detect → vectorize → compute indices → return GeoJSON + metrics.
All data is computed live from real satellite imagery. Zero mock values.
"""

import logging
import uuid

from fastapi import APIRouter, Depends

from backend.auth.firebase_auth import get_current_user, AuthenticatedUser
from backend.database.models import ScanViewportRequest, ScanViewportResponse
from backend.database.db import save_scan_result
from backend.services.tile_fetcher import fetch_and_stitch_tiles
from backend.services.detector import (
    get_detector,
    detect_vegetation_contours,
    detect_water_contours,
    detect_roads_contours,
    detect_built_up_contours,
)
from backend.services.raster_ops import (
    compute_vegetation_percentage,
    compute_image_statistics,
)

logger = logging.getLogger("drishti.api.analysis")
router = APIRouter()

# In-memory store for most recent scan data (used by chat and temporal routes)
_scan_store: dict = {}


def get_scan_store() -> dict:
    """Access the in-memory scan data store."""
    return _scan_store


@router.post("/scan-viewport")
async def scan_viewport(
    request: ScanViewportRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Scan a map viewport:
    1. Fetches live satellite tiles from Esri
    2. Stitches into georeferenced raster
    3. Runs YOLOv8 object detection
    4. Vectorizes vegetation, water, roads, and built-up contours
    5. Computes vegetation percentage from GLI
    6. Returns GeoJSON layers + metrics
    """
    min_lat, min_lon, max_lat, max_lon = request.bbox
    zoom = request.zoom

    logger.info(
        f"Scan request: [{min_lat:.4f}, {min_lon:.4f}, {max_lat:.4f}, {max_lon:.4f}] "
        f"zoom={zoom} user={user.uid}"
    )

    # 1. Fetch and stitch tiles
    result = await fetch_and_stitch_tiles(
        min_lat, min_lon, max_lat, max_lon, zoom, source="current"
    )

    if result is None:
        return {
            "error": "Failed to fetch satellite imagery for this area. "
                     "The tile server may be temporarily unavailable.",
            "scan_id": None,
        }

    image = result["image"]
    transform = result["transform"]
    bounds = result["bounds"]

    # 2. Run YOLOv8 detection
    detector = get_detector()
    detections = detector.detect(image, transform)

    # 3. Vectorize spectral features
    vegetation = detect_vegetation_contours(image, transform)
    water = detect_water_contours(image, transform)
    roads = detect_roads_contours(image, transform)
    built_up = detect_built_up_contours(image, transform)

    # 4. Compute vegetation percentage from actual pixels
    veg_pct = compute_vegetation_percentage(image)

    # 5. Image statistics
    stats = compute_image_statistics(image)

    # 6. Combine all layers
    layers = {
        "detections": detections,
        "vegetation": vegetation,
        "water": water,
        "roads": roads,
        "built_up": built_up,
    }

    # Generate scan ID
    scan_id = str(uuid.uuid4())

    metrics = {
        "detection_count": len(detections.get("features", [])),
        "vegetation_count": len(vegetation.get("features", [])),
        "water_count": len(water.get("features", [])),
        "road_count": len(roads.get("features", [])),
        "built_up_count": len(built_up.get("features", [])),
        "vegetation_percentage": round(veg_pct, 2),
        "image_stats": stats,
    }

    # Store in memory for chat and temporal queries
    _scan_store[scan_id] = {
        "image": image,
        "transform": transform,
        "bounds": bounds,
        "layers": layers,
        "metrics": metrics,
        "zoom": zoom,
        "vegetation_pct": veg_pct,
    }

    # Also keep as "latest" for convenience
    _scan_store["latest"] = _scan_store[scan_id]

    # Save to database
    await save_scan_result({
        "id": scan_id,
        "user_id": user.uid,
        "min_lat": min_lat,
        "min_lon": min_lon,
        "max_lat": max_lat,
        "max_lon": max_lon,
        "zoom": zoom,
        "detection_count": metrics["detection_count"],
        "vegetation_count": metrics["vegetation_count"],
        "water_count": metrics["water_count"],
        "road_count": metrics["road_count"],
        "built_up_count": metrics["built_up_count"],
        "vegetation_pct": veg_pct,
        "image_width": stats["width"],
        "image_height": stats["height"],
        "tile_count": result["tile_count"],
    })

    logger.info(
        f"Scan complete: {scan_id} — "
        f"{metrics['detection_count']} detections, "
        f"{metrics['vegetation_count']} vegetation zones, "
        f"{metrics['water_count']} water bodies, "
        f"{metrics['road_count']} road segments, "
        f"{metrics['built_up_count']} built-up areas, "
        f"vegetation {veg_pct:.1f}%"
    )

    return {
        "scan_id": scan_id,
        "bbox": request.bbox,
        "zoom": zoom,
        "tile_count": result["tile_count"],
        "image_size": {"width": stats["width"], "height": stats["height"]},
        "layers": layers,
        "metrics": metrics,
        "vegetation_percentage": round(veg_pct, 2),
        "bounds": bounds,
    }
