"""
File Upload Route — POST /api/v1/upload

Accepts GeoTIFF, TIFF, PNG, or JPG uploads.
Extracts CRS, affine transform, resolution, and feeds into the detection pipeline.
"""

import io
import logging
import uuid
from pathlib import Path

import numpy as np
from PIL import Image
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from backend.auth.firebase_auth import get_current_user, AuthenticatedUser
from backend.config import get_settings
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

logger = logging.getLogger("drishti.api.ingest")
router = APIRouter()

ALLOWED_EXTENSIONS = {".tif", ".tiff", ".geotiff", ".png", ".jpg", ".jpeg"}


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Upload a GeoTIFF, TIFF, PNG, or JPG for analysis.
    Extracts geospatial metadata if available, then runs the full detection pipeline.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    logger.info(f"Upload: {file.filename} ({file.content_type}) by {user.uid}")

    # Read file content
    content = await file.read()

    # Save to disk
    settings = get_settings()
    upload_id = str(uuid.uuid4())
    save_path = settings.upload_path / f"{upload_id}{ext}"
    save_path.write_bytes(content)
    logger.info(f"Saved upload to {save_path}")

    # Extract image and geospatial metadata
    crs_info = None
    resolution = None
    transform = None
    image = None

    if ext in {".tif", ".tiff", ".geotiff"}:
        try:
            import rasterio
            with rasterio.open(io.BytesIO(content)) as dataset:
                crs_info = str(dataset.crs) if dataset.crs else None
                resolution = {
                    "x": abs(dataset.transform.a) if dataset.transform else None,
                    "y": abs(dataset.transform.e) if dataset.transform else None,
                }

                # Build transform dict from rasterio affine
                if dataset.transform:
                    t = dataset.transform
                    transform = {
                        "origin_lon": float(t.c),
                        "origin_lat": float(t.f),
                        "pixel_width": float(t.a),
                        "pixel_height": float(t.e),
                        "width": dataset.width,
                        "height": dataset.height,
                    }

                # Read bands (handle multi-band rasters)
                if dataset.count >= 3:
                    r = dataset.read(1)
                    g = dataset.read(2)
                    b = dataset.read(3)
                    image = np.stack([r, g, b], axis=-1)
                elif dataset.count == 1:
                    band = dataset.read(1)
                    image = np.stack([band, band, band], axis=-1)
                else:
                    bands = [dataset.read(i + 1) for i in range(dataset.count)]
                    while len(bands) < 3:
                        bands.append(bands[-1])
                    image = np.stack(bands[:3], axis=-1)

                # Normalize to uint8 if needed
                if image.dtype != np.uint8:
                    img_min, img_max = image.min(), image.max()
                    if img_max > img_min:
                        image = ((image - img_min) / (img_max - img_min) * 255).astype(np.uint8)
                    else:
                        image = np.zeros_like(image, dtype=np.uint8)

        except Exception as e:
            logger.warning(f"rasterio failed for {file.filename}: {e}, falling back to PIL")
            image = None

    # Fallback: open with PIL for non-GeoTIFF or if rasterio failed
    if image is None:
        try:
            img = Image.open(io.BytesIO(content)).convert("RGB")
            image = np.array(img)
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Could not read image file: {e}",
            )

    # If no geospatial transform, create a synthetic one (pixel coordinates)
    if transform is None:
        h, w = image.shape[:2]
        transform = {
            "origin_lon": 0.0,
            "origin_lat": 0.0,
            "pixel_width": 1.0 / w,
            "pixel_height": -1.0 / h,
            "width": w,
            "height": h,
        }

    # Run detection pipeline
    detector = get_detector()
    detections = detector.detect(image, transform)
    vegetation = detect_vegetation_contours(image, transform)
    water = detect_water_contours(image, transform)
    roads = detect_roads_contours(image, transform)
    built_up = detect_built_up_contours(image, transform)
    veg_pct = compute_vegetation_percentage(image)
    stats = compute_image_statistics(image)

    layers = {
        "detections": detections,
        "vegetation": vegetation,
        "water": water,
        "roads": roads,
        "built_up": built_up,
    }

    metrics = {
        "detection_count": len(detections.get("features", [])),
        "vegetation_count": len(vegetation.get("features", [])),
        "water_count": len(water.get("features", [])),
        "road_count": len(roads.get("features", [])),
        "built_up_count": len(built_up.get("features", [])),
        "vegetation_percentage": round(veg_pct, 2),
        "image_stats": stats,
    }

    # Encode image to base64 JPEG for display on frontend
    import base64
    pil_img = Image.fromarray(image)
    buf = io.BytesIO()
    pil_img.save(buf, format="JPEG", quality=85)
    image_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")

    bounds = None
    if transform:
        if transform.get("origin_lon") != 0.0 or transform.get("origin_lat") != 0.0:
            # Genuine geospatial bounds (WGS84)
            min_lon = transform["origin_lon"]
            max_lat = transform["origin_lat"]
            max_lon = min_lon + transform["pixel_width"] * transform["width"]
            min_lat = max_lat + transform["pixel_height"] * transform["height"]
            bounds = [min_lat, min_lon, max_lat, max_lon]
        else:
            # Synthetic transform bounds (0..1 normalized pixel space)
            bounds = [-1.0, 0.0, 0.0, 1.0]

    # Store in scan store for chat
    from backend.api.routes_analysis import _scan_store
    scan_id = upload_id
    _scan_store[scan_id] = {
        "image": image,
        "transform": transform,
        "bounds": bounds,
        "layers": layers,
        "metrics": metrics,
        "zoom": 15,
        "vegetation_pct": veg_pct,
    }
    _scan_store["latest"] = _scan_store[scan_id]

    logger.info(
        f"Upload analysis complete: {scan_id} — "
        f"{metrics['detection_count']} detections, "
        f"vegetation {veg_pct:.1f}%"
    )

    return {
        "scan_id": scan_id,
        "filename": file.filename,
        "file_type": ext,
        "image_size": {"width": stats["width"], "height": stats["height"]},
        "crs": crs_info,
        "resolution": resolution,
        "layers": layers,
        "metrics": metrics,
        "image_base64": image_base64,
        "bounds": bounds,
    }

