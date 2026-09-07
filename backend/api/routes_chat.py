"""
Chat Route — POST /api/v1/chat

Grounded conversational engine that answers spatial questions
using computed GeoJSON data. Returns evidence feature IDs for map highlighting.
"""

import logging

from fastapi import APIRouter, Depends

from backend.auth.firebase_auth import get_current_user, AuthenticatedUser
from backend.database.models import ChatRequest, ChatResponse
from backend.database.db import save_chat_log
from backend.services.grounding_checker import get_grounding_engine
from backend.api.routes_analysis import get_scan_store

logger = logging.getLogger("drishti.api.chat")
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Process a natural language spatial question.
    Queries the computed GeoJSON store and returns a grounded answer
    with evidence feature IDs for map highlighting.
    """
    scan_store = get_scan_store()

    # Get scan data — use specific scan_id or latest
    scan_id = request.scan_id or "latest"
    scan_data = scan_store.get(scan_id)

    if scan_data is None and scan_id != "latest":
        # Try latest as fallback
        scan_data = scan_store.get("latest")

    # Prepare context for the grounding engine
    current_geojson = None
    past_geojson = None
    temporal_metrics = None
    vegetation_pct = None
    bounds = None

    if scan_data:
        # Combine all current layers into one FeatureCollection
        layers = scan_data.get("layers", {})
        all_features = []
        for layer_name, layer_geojson in layers.items():
            if isinstance(layer_geojson, dict):
                all_features.extend(layer_geojson.get("features", []))

        current_geojson = {"type": "FeatureCollection", "features": all_features}

        # Past layers if available
        past_layers = scan_data.get("past_layers", {})
        if past_layers:
            past_features = []
            for layer_geojson in past_layers.values():
                if isinstance(layer_geojson, dict):
                    past_features.extend(layer_geojson.get("features", []))
            past_geojson = {"type": "FeatureCollection", "features": past_features}

        temporal_metrics = scan_data.get("temporal_metrics")
        vegetation_pct = scan_data.get("vegetation_pct")
        bounds = scan_data.get("bounds")

    # Query the grounding engine
    engine = get_grounding_engine()
    result = engine.query(
        question=request.message,
        current_geojson=current_geojson,
        past_geojson=past_geojson,
        temporal_metrics=temporal_metrics,
        vegetation_pct=vegetation_pct,
        bounds=bounds,
    )

    # Save chat log
    await save_chat_log({
        "scan_id": scan_id if scan_id != "latest" else None,
        "user_id": user.uid,
        "question": request.message,
        "answer": result["answer"],
        "evidence_ids": result["evidence_ids"],
        "confidence": result["confidence"],
        "data_source": result["data_source"],
    })

    logger.info(
        f"Chat: '{request.message[:50]}...' → "
        f"confidence={result['confidence']}, "
        f"evidence_count={len(result['evidence_ids'])}"
    )

    return ChatResponse(
        answer=result["answer"],
        evidence_ids=result["evidence_ids"],
        confidence=result["confidence"],
        data_source=result["data_source"],
    )
