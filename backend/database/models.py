"""
Database Models — Pydantic models for API request/response validation.
These define the contract between frontend and backend.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ScanViewportRequest(BaseModel):
    """Request body for POST /api/v1/scan-viewport"""
    bbox: list[float] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="[min_lat, min_lon, max_lat, max_lon] in WGS84",
    )
    zoom: int = Field(default=15, ge=1, le=20, description="Map zoom level")


class ScanViewportResponse(BaseModel):
    """Response from scan-viewport endpoint"""
    scan_id: str
    bbox: list[float]
    zoom: int
    tile_count: int
    image_size: dict  # {width, height}
    layers: dict  # {detections, vegetation, water, roads, built_up} — GeoJSON FeatureCollections
    metrics: dict  # Computed metrics
    vegetation_percentage: float
    bounds: dict  # Actual bounds of stitched tiles


class TemporalAnalysisRequest(BaseModel):
    """Request body for POST /api/v1/temporal-analysis"""
    bbox: list[float] = Field(..., min_length=4, max_length=4)
    zoom: int = Field(default=15, ge=1, le=20)
    year: int = Field(default=2021, ge=2000, le=2026)


class TemporalAnalysisResponse(BaseModel):
    """Response from temporal analysis"""
    scan_id: str
    current_layers: dict
    past_layers: dict
    growth_metrics: dict
    current_bounds: dict
    past_bounds: dict
    current_image_base64: Optional[str] = None
    past_image_base64: Optional[str] = None


class ChatRequest(BaseModel):
    """Request body for POST /api/v1/chat"""
    message: str = Field(..., min_length=1, max_length=2000)
    scan_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from chat endpoint"""
    answer: str
    evidence_ids: list[str] = []
    confidence: str = "none"
    data_source: str = ""


class ReportExportRequest(BaseModel):
    """Request body for POST /api/v1/reports/export"""
    scan_id: str
    include_temporal: bool = True
    title: Optional[str] = "DrishtiAI Intelligence Report"


class UploadResponse(BaseModel):
    """Response from file upload"""
    scan_id: str
    filename: str
    file_type: str
    image_size: dict
    crs: Optional[str] = None
    resolution: Optional[dict] = None
    layers: dict
    metrics: dict
