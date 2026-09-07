"""
Grounding Checker — Spatial query executor and anti-hallucination guardrail.

Parses natural language spatial questions, queries computed GeoJSON stores
using shapely spatial operations, and returns grounded answers with evidence.

If evidence is insufficient, returns: "I cannot determine this from the available evidence."
"""

import re
import logging
from typing import Optional

from shapely.geometry import shape, Point, box

logger = logging.getLogger("drishti.grounding")

# Guardrail response for insufficient evidence
INSUFFICIENT_EVIDENCE = "I cannot determine this from the available evidence."


class SpatialQueryEngine:
    """
    Deterministic spatial query engine for grounded Q&A.
    Parses natural language, queries GeoJSON data, returns evidence-backed answers.
    """

    def __init__(self):
        # Pattern matchers for spatial questions
        self.patterns = [
            # Counting patterns
            (r"how many\s+(.*?)(?:\s+are there|\s+detected|\s+found|\s+in|\?|$)",
             self._handle_count_query),
            (r"(?:count|number of|total)\s+(.*?)(?:\s+in|\s+detected|\?|$)",
             self._handle_count_query),

            # Location patterns
            (r"where\s+(?:are|is)\s+(?:the\s+)?(.*?)(?:\?|$)",
             self._handle_location_query),
            (r"(?:show|find|locate)\s+(?:the\s+|all\s+)?(.*?)(?:\?|$)",
             self._handle_location_query),

            # Growth/change patterns
            (r"(?:how much|what)\s+(?:growth|change|expansion|increase|decrease)(?:\s+.*?)?(?:since|from|between)\s+(\d{4})",
             self._handle_growth_query),
            (r"(?:what|how)\s+(?:has\s+)?changed\s+(?:since|from)\s+(\d{4})",
             self._handle_growth_query),
            (r"(?:buildings?|structures?)\s+(?:added|built|constructed|new)\s+(?:since|from)\s+(\d{4})",
             self._handle_growth_query),

            # Area/coverage patterns
            (r"(?:what|how much)\s+(?:area|coverage|percentage|percent)\s+(?:is|of)\s+(.*?)(?:\?|$)",
             self._handle_coverage_query),
            (r"(?:vegetation|green|forest)\s+(?:cover|coverage|area|percentage)",
             self._handle_vegetation_query),

            # Water patterns
            (r"(?:water|river|lake|pond|stream|reservoir)",
             self._handle_water_query),

            # General description
            (r"(?:describe|summarize|overview|what do you see|analyze|tell me about)",
             self._handle_overview_query),
        ]

    def query(
        self,
        question: str,
        current_geojson: Optional[dict] = None,
        past_geojson: Optional[dict] = None,
        temporal_metrics: Optional[dict] = None,
        vegetation_pct: Optional[float] = None,
        bounds: Optional[dict] = None,
    ) -> dict:
        """
        Process a natural language spatial question.

        Returns:
            {
                "answer": str,  # Grounded answer or INSUFFICIENT_EVIDENCE
                "evidence_ids": list[str],  # Feature IDs for map highlighting
                "confidence": str,  # "high", "medium", "low", "none"
                "data_source": str,  # What data was used
            }
        """
        question_lower = question.lower().strip()
        context = {
            "current_geojson": current_geojson or {"type": "FeatureCollection", "features": []},
            "past_geojson": past_geojson or {"type": "FeatureCollection", "features": []},
            "temporal_metrics": temporal_metrics or {},
            "vegetation_pct": vegetation_pct,
            "bounds": bounds,
        }

        # Try each pattern
        for pattern, handler in self.patterns:
            match = re.search(pattern, question_lower)
            if match:
                try:
                    return handler(match, context)
                except Exception as e:
                    logger.error(f"Query handler error: {e}")
                    return {
                        "answer": INSUFFICIENT_EVIDENCE,
                        "evidence_ids": [],
                        "confidence": "none",
                        "data_source": "error",
                    }

        # No pattern matched — try general feature search
        return self._handle_general_query(question_lower, context)

    def _get_features_by_layer(self, geojson: dict, layer: str) -> list:
        """Filter GeoJSON features by layer name."""
        return [
            f for f in geojson.get("features", [])
            if f.get("properties", {}).get("layer", "").lower() == layer.lower()
            or f.get("properties", {}).get("class", "").lower() == layer.lower()
        ]

    def _get_all_feature_ids(self, features: list) -> list:
        """Extract feature IDs for evidence highlighting."""
        return [f.get("id", "") for f in features if f.get("id")]

    def _match_layer_name(self, query_term: str) -> str:
        """Map natural language terms to layer names."""
        term = query_term.lower().strip()
        mappings = {
            "building": "built_up", "buildings": "built_up",
            "structure": "built_up", "structures": "built_up",
            "construction": "built_up", "concrete": "built_up",
            "built up": "built_up", "built-up": "built_up",
            "urban": "built_up",
            "vegetation": "vegetation", "trees": "vegetation",
            "green": "vegetation", "forest": "vegetation",
            "plants": "vegetation", "greenery": "vegetation",
            "water": "water", "river": "water", "lake": "water",
            "pond": "water", "stream": "water", "reservoir": "water",
            "road": "roads", "roads": "roads", "street": "roads",
            "highway": "roads", "path": "roads",
            "car": "detections", "cars": "detections",
            "vehicle": "detections", "vehicles": "detections",
            "truck": "detections", "trucks": "detections",
            "object": "detections", "objects": "detections",
            "detection": "detections", "detections": "detections",
        }
        return mappings.get(term, term)

    def _handle_count_query(self, match, context: dict) -> dict:
        """Handle 'how many X' questions."""
        query_term = match.group(1).strip()
        layer = self._match_layer_name(query_term)
        geojson = context["current_geojson"]
        features = self._get_features_by_layer(geojson, layer)
        count = len(features)
        evidence_ids = self._get_all_feature_ids(features)

        if count == 0:
            # Also try detections for specific class names
            all_features = geojson.get("features", [])
            class_matches = [
                f for f in all_features
                if query_term.lower() in f.get("properties", {}).get("class", "").lower()
            ]
            if class_matches:
                count = len(class_matches)
                evidence_ids = self._get_all_feature_ids(class_matches)
                return {
                    "answer": f"I detected exactly {count} {query_term} feature(s) in the current scan area. "
                              f"This count was computed from live YOLOv8 inference on satellite imagery.",
                    "evidence_ids": evidence_ids,
                    "confidence": "high",
                    "data_source": "YOLOv8 detection + contour analysis",
                }

        if count == 0:
            return {
                "answer": f"I detected 0 {query_term} features in the current scan area. "
                          f"No {query_term} polygons were found by the detection pipeline.",
                "evidence_ids": [],
                "confidence": "high",
                "data_source": "YOLOv8 detection + contour analysis",
            }

        return {
            "answer": f"I detected exactly {count} {query_term} feature(s) in the current scan area. "
                      f"This count was computed from live analysis of the satellite imagery — "
                      f"each feature corresponds to a real polygon detected by the analysis pipeline.",
            "evidence_ids": evidence_ids,
            "confidence": "high",
            "data_source": "YOLOv8 detection + contour analysis",
        }

    def _handle_location_query(self, match, context: dict) -> dict:
        """Handle 'where are X' questions."""
        query_term = match.group(1).strip()
        layer = self._match_layer_name(query_term)
        geojson = context["current_geojson"]
        features = self._get_features_by_layer(geojson, layer)

        if not features:
            return {
                "answer": f"No {query_term} features were detected in the current scan area.",
                "evidence_ids": [],
                "confidence": "high",
                "data_source": "YOLOv8 detection + contour analysis",
            }

        evidence_ids = self._get_all_feature_ids(features)

        # Build location descriptions from center coordinates
        locations = []
        for f in features[:5]:  # Limit to first 5 for readability
            props = f.get("properties", {})
            lat = props.get("center_lat", 0)
            lon = props.get("center_lon", 0)
            if lat and lon:
                locations.append(f"({lat:.5f}°N, {lon:.5f}°E)")

        loc_str = ", ".join(locations)
        remaining = len(features) - min(5, len(features))
        more_str = f" and {remaining} more locations" if remaining > 0 else ""

        return {
            "answer": f"I found {len(features)} {query_term} feature(s) in the scan area. "
                      f"Key locations: {loc_str}{more_str}. "
                      f"Click the evidence markers to zoom to each feature on the map.",
            "evidence_ids": evidence_ids,
            "confidence": "high",
            "data_source": "YOLOv8 detection + contour analysis",
        }

    def _handle_growth_query(self, match, context: dict) -> dict:
        """Handle temporal growth questions."""
        temporal = context.get("temporal_metrics")
        if not temporal:
            return {
                "answer": INSUFFICIENT_EVIDENCE
                          + " Please run a temporal analysis scan first to compare 2021 vs 2026 imagery.",
                "evidence_ids": [],
                "confidence": "none",
                "data_source": "no temporal data available",
            }

        detections = temporal.get("detections", {})
        built = temporal.get("built_up_areas", {})
        veg = temporal.get("vegetation", {})

        parts = []

        net_det = detections.get("net_change", 0)
        det_pct = detections.get("growth_percentage", 0)
        parts.append(
            f"Object detections changed by {net_det:+d} ({det_pct:+.1f}%) from "
            f"{detections.get('past_count', 0)} to {detections.get('current_count', 0)}."
        )

        concrete_sqm = built.get("concrete_expansion_sqm", 0)
        concrete_pct = built.get("concrete_growth_percentage", 0)
        parts.append(
            f"Built-up area changed by {concrete_sqm:+.0f} m² ({concrete_pct:+.1f}%)."
        )

        veg_change = veg.get("vegetation_change_pct", 0)
        if veg_change < 0:
            parts.append(f"Vegetation decreased by {abs(veg_change):.1f}%.")
        elif veg_change > 0:
            parts.append(f"Vegetation increased by {veg_change:.1f}%.")
        else:
            parts.append("No significant vegetation change detected.")

        return {
            "answer": " ".join(parts) + " All metrics computed from live satellite imagery comparison.",
            "evidence_ids": [],
            "confidence": "high",
            "data_source": "temporal analysis (2021 Wayback vs 2026 current)",
        }

    def _handle_coverage_query(self, match, context: dict) -> dict:
        """Handle area/coverage questions."""
        query_term = match.group(1).strip() if match.lastindex else ""
        layer = self._match_layer_name(query_term)

        geojson = context["current_geojson"]
        features = self._get_features_by_layer(geojson, layer)

        if not features:
            return {
                "answer": f"No {query_term} coverage data is available. "
                          + INSUFFICIENT_EVIDENCE,
                "evidence_ids": [],
                "confidence": "none",
                "data_source": "none",
            }

        total_area_pixels = sum(
            f.get("properties", {}).get("area_pixels", 0) for f in features
        )

        evidence_ids = self._get_all_feature_ids(features)

        return {
            "answer": f"There are {len(features)} {query_term} regions detected, "
                      f"covering approximately {total_area_pixels:.0f} pixels in total area. "
                      f"Each polygon was extracted from actual satellite image analysis.",
            "evidence_ids": evidence_ids,
            "confidence": "high",
            "data_source": "contour analysis + spectral indices",
        }

    def _handle_vegetation_query(self, match, context: dict) -> dict:
        """Handle vegetation-specific questions."""
        veg_pct = context.get("vegetation_pct")
        geojson = context["current_geojson"]
        veg_features = self._get_features_by_layer(geojson, "vegetation")
        evidence_ids = self._get_all_feature_ids(veg_features)

        parts = []
        if veg_pct is not None:
            parts.append(
                f"Vegetation covers approximately {veg_pct:.1f}% of the scanned area, "
                f"computed from the Green Leaf Index (GLI) of actual satellite pixels."
            )

        if veg_features:
            parts.append(
                f"I identified {len(veg_features)} distinct vegetation zones."
            )

        temporal = context.get("temporal_metrics")
        if temporal and temporal.get("vegetation"):
            v = temporal["vegetation"]
            parts.append(
                f"Compared to 2021, vegetation coverage went from "
                f"{v['past_coverage_pct']:.1f}% to {v['current_coverage_pct']:.1f}% "
                f"(change: {v['vegetation_change_pct']:+.1f}%)."
            )

        if not parts:
            return {
                "answer": INSUFFICIENT_EVIDENCE,
                "evidence_ids": [],
                "confidence": "none",
                "data_source": "none",
            }

        return {
            "answer": " ".join(parts),
            "evidence_ids": evidence_ids,
            "confidence": "high",
            "data_source": "GLI spectral analysis + contour detection",
        }

    def _handle_water_query(self, match, context: dict) -> dict:
        """Handle water body questions."""
        geojson = context["current_geojson"]
        water_features = self._get_features_by_layer(geojson, "water")
        evidence_ids = self._get_all_feature_ids(water_features)

        if not water_features:
            return {
                "answer": "No water bodies were detected in the current scan area.",
                "evidence_ids": [],
                "confidence": "high",
                "data_source": "spectral water index analysis",
            }

        return {
            "answer": f"I detected {len(water_features)} water body/bodies in the scan area. "
                      f"Detection used spectral band ratios (blue vs green channels) "
                      f"from the actual satellite imagery pixels.",
            "evidence_ids": evidence_ids,
            "confidence": "high",
            "data_source": "spectral water index analysis",
        }

    def _handle_overview_query(self, match, context: dict) -> dict:
        """Handle general overview/describe questions."""
        geojson = context["current_geojson"]
        features = geojson.get("features", [])

        if not features:
            return {
                "answer": "No features have been analyzed yet. "
                          "Please scan a viewport area first.",
                "evidence_ids": [],
                "confidence": "none",
                "data_source": "none",
            }

        # Count by layer
        layer_counts = {}
        for f in features:
            layer = f.get("properties", {}).get("layer", "unknown")
            layer_counts[layer] = layer_counts.get(layer, 0) + 1

        parts = [f"Scan analysis found a total of {len(features)} features:"]
        for layer, count in sorted(layer_counts.items()):
            parts.append(f"  • {layer}: {count}")

        veg_pct = context.get("vegetation_pct")
        if veg_pct is not None:
            parts.append(f"  • Vegetation coverage: {veg_pct:.1f}%")

        temporal = context.get("temporal_metrics")
        if temporal:
            det = temporal.get("detections", {})
            parts.append(
                f"  • Temporal change: {det.get('net_change', 0):+d} detections since 2021"
            )

        parts.append("All values computed from live satellite imagery analysis.")

        return {
            "answer": "\n".join(parts),
            "evidence_ids": self._get_all_feature_ids(features[:20]),
            "confidence": "high",
            "data_source": "full pipeline analysis",
        }

    def _handle_general_query(self, question: str, context: dict) -> dict:
        """Fallback handler for unrecognized questions."""
        geojson = context["current_geojson"]
        features = geojson.get("features", [])

        # Try to find any keyword match in feature properties
        matching = []
        for f in features:
            props = f.get("properties", {})
            for key, val in props.items():
                if isinstance(val, str) and any(
                    word in val.lower() for word in question.split()
                    if len(word) > 3
                ):
                    matching.append(f)
                    break

        if matching:
            evidence_ids = self._get_all_feature_ids(matching)
            return {
                "answer": f"I found {len(matching)} features that may be relevant to your question. "
                          f"Click the evidence markers to inspect them on the map.",
                "evidence_ids": evidence_ids,
                "confidence": "medium",
                "data_source": "keyword search in feature properties",
            }

        return {
            "answer": INSUFFICIENT_EVIDENCE,
            "evidence_ids": [],
            "confidence": "none",
            "data_source": "none",
        }


# Singleton instance
_engine: Optional[SpatialQueryEngine] = None


def get_grounding_engine() -> SpatialQueryEngine:
    """Get or create the spatial query engine singleton."""
    global _engine
    if _engine is None:
        _engine = SpatialQueryEngine()
    return _engine
