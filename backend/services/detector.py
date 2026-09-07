"""
Object Detector — YOLOv8 inference + OpenCV contour vectorization.

Uses ultralytics YOLOv8 for structural detection and OpenCV for
road/water boundary contour extraction. All results are real detections
from actual image data — zero mock values.

Device selection: MPS (Apple Silicon) > CUDA (NVIDIA) > CPU
"""

import logging
from functools import lru_cache
from typing import Optional
import uuid

import cv2
import numpy as np

from backend.config import get_settings
from backend.services.raster_ops import (
    pixel_to_wgs84,
    pixel_polygon_to_wgs84,
    compute_vegetation_mask,
    compute_water_mask,
    compute_built_up_mask,
)

logger = logging.getLogger("drishti.detector")


class ObjectDetector:
    """
    Wraps YOLOv8 for satellite image object detection.
    Auto-downloads model weights on first initialization.
    """

    def __init__(self):
        settings = get_settings()
        self.device = settings.device

        logger.info(f"Loading YOLO model '{settings.yolo_model_path}' on device '{self.device}'...")
        from ultralytics import YOLO
        self.model = YOLO(settings.yolo_model_path)
        logger.info("YOLO model loaded successfully.")

        # COCO class names that are relevant for satellite/overhead imagery
        self.structural_classes = {
            "car", "truck", "bus", "train", "boat",
            "airplane", "bicycle", "motorcycle",
        }
        self.all_class_names = self.model.names if hasattr(self.model, "names") else {}

    def detect(
        self, image: np.ndarray, transform: dict, confidence: float = 0.25
    ) -> dict:
        """
        Run YOLOv8 inference on an image and convert detections to GeoJSON.

        Args:
            image: RGB numpy array
            transform: Affine transform dict from tile stitching
            confidence: Minimum confidence threshold

        Returns:
            GeoJSON FeatureCollection with real bounding box polygons
            in WGS84 coordinates. Zero mock data.
        """
        results = self.model.predict(
            source=image,
            conf=confidence,
            device=self.device,
            verbose=False,
        )

        features = []
        for result in results:
            if result.boxes is None:
                continue

            boxes = result.boxes
            for i in range(len(boxes)):
                # Extract real bounding box coordinates
                xyxy = boxes.xyxy[i].cpu().numpy()
                x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])

                conf = float(boxes.conf[i].cpu().numpy())
                cls_id = int(boxes.cls[i].cpu().numpy())
                cls_name = self.all_class_names.get(cls_id, f"class_{cls_id}")

                # Convert pixel bbox to WGS84 polygon
                tl_lat, tl_lon = pixel_to_wgs84(x1, y1, transform)
                tr_lat, tr_lon = pixel_to_wgs84(x2, y1, transform)
                br_lat, br_lon = pixel_to_wgs84(x2, y2, transform)
                bl_lat, bl_lon = pixel_to_wgs84(x1, y2, transform)

                polygon_coords = [
                    [tl_lon, tl_lat],
                    [tr_lon, tr_lat],
                    [br_lon, br_lat],
                    [bl_lon, bl_lat],
                    [tl_lon, tl_lat],  # Close polygon
                ]

                # Compute center point
                center_lat, center_lon = pixel_to_wgs84(
                    (x1 + x2) / 2, (y1 + y2) / 2, transform
                )

                feature = {
                    "type": "Feature",
                    "id": str(uuid.uuid4()),
                    "properties": {
                        "class": cls_name,
                        "confidence": round(conf, 4),
                        "class_id": cls_id,
                        "layer": "detections",
                        "pixel_bbox": [x1, y1, x2, y2],
                        "center_lat": center_lat,
                        "center_lon": center_lon,
                    },
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [polygon_coords],
                    },
                }
                features.append(feature)

        logger.info(f"YOLOv8 detected {len(features)} objects on device '{self.device}'")

        return {
            "type": "FeatureCollection",
            "features": features,
        }


def vectorize_contours(
    mask: np.ndarray,
    transform: dict,
    layer_name: str,
    min_area: int = 50,
    simplify_epsilon: float = 2.0,
) -> dict:
    """
    Convert a binary mask to GeoJSON polygons via OpenCV contour detection.

    Args:
        mask: Binary numpy array (True/1 = feature present)
        transform: Affine transform for pixel→WGS84 conversion
        layer_name: Name for the GeoJSON layer property
        min_area: Minimum contour area in pixels to keep
        simplify_epsilon: Douglas-Peucker simplification tolerance

    Returns:
        GeoJSON FeatureCollection — real polygons from actual image data
    """
    # Convert boolean mask to uint8 for OpenCV
    mask_uint8 = (mask.astype(np.uint8)) * 255

    contours, _ = cv2.findContours(
        mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    features = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < min_area:
            continue

        # Simplify contour to reduce point count
        simplified = cv2.approxPolyDP(contour, simplify_epsilon, True)

        if len(simplified) < 3:
            continue

        # Convert pixel contour to WGS84 coordinates
        coords = pixel_polygon_to_wgs84(simplified, transform)

        if len(coords) < 4:  # Need at least 3 points + closing point
            continue

        # Compute centroid from pixel space
        M = cv2.moments(contour)
        if M["m00"] > 0:
            cx = M["m10"] / M["m00"]
            cy = M["m01"] / M["m00"]
            center_lat, center_lon = pixel_to_wgs84(cx, cy, transform)
        else:
            center_lat, center_lon = 0.0, 0.0

        feature = {
            "type": "Feature",
            "id": str(uuid.uuid4()),
            "properties": {
                "layer": layer_name,
                "area_pixels": float(area),
                "perimeter_pixels": float(cv2.arcLength(contour, True)),
                "center_lat": center_lat,
                "center_lon": center_lon,
                "vertex_count": len(simplified),
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [coords],
            },
        }
        features.append(feature)

    logger.info(f"Vectorized {len(features)} {layer_name} polygons from contour analysis")

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def detect_roads_contours(image: np.ndarray, transform: dict) -> dict:
    """
    Detect road-like features using edge detection and morphological operations.
    Returns GeoJSON FeatureCollection of road contours.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)

    # Edge detection
    edges = cv2.Canny(gray, 50, 150)

    # Morphological close to connect road segments
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=2)

    # Dilate to thicken road lines
    dilated = cv2.dilate(closed, kernel, iterations=1)

    return vectorize_contours(dilated > 0, transform, "roads", min_area=100)


def detect_vegetation_contours(image: np.ndarray, transform: dict) -> dict:
    """
    Detect vegetation areas using GLI-based mask.
    Returns GeoJSON FeatureCollection of vegetation polygons.
    """
    veg_mask = compute_vegetation_mask(image, threshold=0.05)

    # Clean up with morphological operations
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    cleaned = cv2.morphologyEx(
        veg_mask.astype(np.uint8) * 255, cv2.MORPH_OPEN, kernel
    )
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel)

    return vectorize_contours(cleaned > 0, transform, "vegetation", min_area=200)


def detect_water_contours(image: np.ndarray, transform: dict) -> dict:
    """
    Detect water bodies using spectral analysis.
    Returns GeoJSON FeatureCollection of water polygons.
    """
    water_mask = compute_water_mask(image)

    # Clean up
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    cleaned = cv2.morphologyEx(
        water_mask.astype(np.uint8) * 255, cv2.MORPH_CLOSE, kernel, iterations=2
    )

    return vectorize_contours(cleaned > 0, transform, "water", min_area=300)


def detect_built_up_contours(image: np.ndarray, transform: dict) -> dict:
    """
    Detect built-up/concrete areas using spectral analysis.
    Returns GeoJSON FeatureCollection of built-up polygons.
    """
    built_mask = compute_built_up_mask(image)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    cleaned = cv2.morphologyEx(
        built_mask.astype(np.uint8) * 255, cv2.MORPH_CLOSE, kernel
    )

    return vectorize_contours(cleaned > 0, transform, "built_up", min_area=200)


@lru_cache()
def get_detector() -> ObjectDetector:
    """Singleton YOLO detector instance."""
    return ObjectDetector()
