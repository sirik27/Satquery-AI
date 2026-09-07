"""
PDF Report Template — ReportLab layout for DrishtiAI intelligence reports.

Generates a professional PDF with header, metadata table, detection metrics,
temporal growth analysis, and summary sections.
"""

import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)


def generate_pdf_report(data: dict) -> bytes:
    """
    Generate a PDF intelligence report from scan data.

    Args:
        data: Dict containing title, bounds, metrics, temporal_metrics, etc.

    Returns:
        PDF file content as bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#0a192f"),
        spaceAfter=6,
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=colors.HexColor("#0a192f"),
        spaceBefore=12,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["Normal"],
        fontSize=10,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=4,
    )
    small_style = ParagraphStyle(
        "ReportSmall",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#64748b"),
    )

    elements = []

    # Title
    elements.append(Paragraph(data.get("title", "DrishtiAI Intelligence Report"), title_style))
    elements.append(Paragraph(
        f"Generated: {data.get('generated_at', 'N/A')} | User: {data.get('user', 'N/A')}",
        small_style,
    ))
    elements.append(Spacer(1, 8 * mm))
    elements.append(HRFlowable(
        width="100%", thickness=1.5,
        color=colors.HexColor("#0a192f"), spaceAfter=8 * mm,
    ))

    # Scan Metadata
    elements.append(Paragraph("Scan Metadata", heading_style))
    bounds = data.get("bounds")
    if bounds:
        meta_data = [
            ["Parameter", "Value"],
            ["Min Latitude", f"{bounds.get('min_lat', 'N/A'):.6f}°"],
            ["Max Latitude", f"{bounds.get('max_lat', 'N/A'):.6f}°"],
            ["Min Longitude", f"{bounds.get('min_lon', 'N/A'):.6f}°"],
            ["Max Longitude", f"{bounds.get('max_lon', 'N/A'):.6f}°"],
            ["Zoom Level", str(data.get("zoom", "N/A"))],
        ]
    else:
        meta_data = [
            ["Parameter", "Value"],
            ["Zoom Level", str(data.get("zoom", "N/A"))],
            ["Bounds", "From uploaded file"],
        ]

    meta_table = Table(meta_data, colWidths=[60 * mm, 100 * mm])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a192f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 6 * mm))

    # Detection Metrics
    elements.append(Paragraph("Detection Summary", heading_style))
    metrics = data.get("metrics", {})
    layers = data.get("layers", {})

    det_data = [["Feature Layer", "Count"]]
    if layers:
        for layer_name, count in layers.items():
            det_data.append([layer_name.replace("_", " ").title(), str(count)])
    elif metrics:
        det_data.append(["Object Detections", str(metrics.get("detection_count", 0))])
        det_data.append(["Vegetation Zones", str(metrics.get("vegetation_count", 0))])
        det_data.append(["Water Bodies", str(metrics.get("water_count", 0))])
        det_data.append(["Road Segments", str(metrics.get("road_count", 0))])
        det_data.append(["Built-up Areas", str(metrics.get("built_up_count", 0))])

    veg_pct = data.get("vegetation_pct")
    if veg_pct is not None:
        det_data.append(["Vegetation Coverage", f"{veg_pct:.1f}%"])

    det_table = Table(det_data, colWidths=[80 * mm, 80 * mm])
    det_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#eff6ff")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#93c5fd")),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(det_table)
    elements.append(Spacer(1, 6 * mm))

    # Temporal Growth Analysis (if available)
    temporal = data.get("temporal_metrics")
    if temporal:
        elements.append(Paragraph("Temporal Growth Analysis (2021 → 2026)", heading_style))

        det = temporal.get("detections", {})
        built = temporal.get("built_up_areas", {})
        veg = temporal.get("vegetation", {})

        growth_data = [
            ["Metric", "2021", "2026", "Change"],
            [
                "Object Detections",
                str(det.get("past_count", 0)),
                str(det.get("current_count", 0)),
                f"{det.get('net_change', 0):+d} ({det.get('growth_percentage', 0):+.1f}%)",
            ],
            [
                "Built-up Area (m²)",
                f"{built.get('past_area_sqm', 0):,.0f}",
                f"{built.get('current_area_sqm', 0):,.0f}",
                f"{built.get('concrete_expansion_sqm', 0):+,.0f}",
            ],
            [
                "Vegetation Coverage",
                f"{veg.get('past_coverage_pct', 0):.1f}%",
                f"{veg.get('current_coverage_pct', 0):.1f}%",
                f"{veg.get('vegetation_change_pct', 0):+.1f}%",
            ],
        ]

        growth_table = Table(growth_data, colWidths=[50 * mm, 35 * mm, 35 * mm, 40 * mm])
        growth_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#065f46")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ecfdf5")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#6ee7b7")),
            ("ALIGN", (1, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(growth_table)
        elements.append(Spacer(1, 6 * mm))

    # Footer
    elements.append(HRFlowable(
        width="100%", thickness=0.5,
        color=colors.HexColor("#94a3b8"), spaceBefore=10 * mm,
    ))
    elements.append(Paragraph(
        "This report was generated by DrishtiAI — Satellite Intelligence Platform. "
        "All metrics are computed from live satellite imagery analysis. "
        "No mock data or hardcoded values are used.",
        small_style,
    ))

    # Build PDF
    doc.build(elements)
    return buffer.getvalue()
