"""
Reports Route — POST /api/v1/reports/export

Generates a formal PDF intelligence summary using ReportLab.
Contains bounding coordinates, acquisition dates, calculated growth metrics,
detected feature counts, and analysis summary.
"""

import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from backend.auth.firebase_auth import get_current_user, AuthenticatedUser
from backend.database.models import ReportExportRequest
from backend.api.routes_analysis import get_scan_store
from backend.templates.report_template import generate_pdf_report

logger = logging.getLogger("drishti.api.reports")
router = APIRouter()


@router.post("/reports/export")
async def export_report(
    request: ReportExportRequest,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Generate and return a PDF intelligence report for a scan.
    All data in the report comes from computed analysis — zero mock values.
    """
    scan_store = get_scan_store()
    scan_data = scan_store.get(request.scan_id)

    if scan_data is None:
        scan_data = scan_store.get("latest")

    if scan_data is None:
        return {"error": "No scan data available. Please run a scan first."}

    # Gather report data
    report_data = {
        "title": request.title or "DrishtiAI Intelligence Report",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user": user.email or user.uid,
        "bounds": scan_data.get("bounds"),
        "zoom": scan_data.get("zoom"),
        "metrics": scan_data.get("metrics", {}),
        "vegetation_pct": scan_data.get("vegetation_pct"),
        "temporal_metrics": scan_data.get("temporal_metrics"),
        "layers": {},
    }

    # Count features per layer
    layers = scan_data.get("layers", {})
    for layer_name, geojson in layers.items():
        if isinstance(geojson, dict):
            report_data["layers"][layer_name] = len(geojson.get("features", []))

    # Generate PDF
    pdf_buffer = generate_pdf_report(report_data)

    logger.info(f"Generated report for scan {request.scan_id}")

    return StreamingResponse(
        io.BytesIO(pdf_buffer),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=DrishtiAI_Report_{request.scan_id[:8]}.pdf"
        },
    )
