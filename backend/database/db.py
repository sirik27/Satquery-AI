"""
Database — SQLite cross-platform local database using aiosqlite.
All paths use pathlib.Path for Windows/macOS compatibility.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import aiosqlite

from backend.config import get_settings

logger = logging.getLogger("drishti.db")

_db_path: Optional[Path] = None


def _get_db_path() -> Path:
    """Get the SQLite database file path (cross-platform)."""
    global _db_path
    if _db_path is not None:
        return _db_path

    settings = get_settings()
    # Parse sqlite:/// prefix
    url = settings.database_url
    if url.startswith("sqlite:///"):
        db_file = url[len("sqlite:///"):]
    else:
        db_file = "data/drishti.db"

    _db_path = Path(db_file).resolve()
    _db_path.parent.mkdir(parents=True, exist_ok=True)
    return _db_path


async def get_connection() -> aiosqlite.Connection:
    """Get an async SQLite connection."""
    db_path = _get_db_path()
    conn = await aiosqlite.connect(str(db_path))
    conn.row_factory = aiosqlite.Row
    return conn


async def init_db():
    """Initialize database tables."""
    db_path = _get_db_path()
    logger.info(f"Initializing database at {db_path}")

    async with aiosqlite.connect(str(db_path)) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS scan_results (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                user_id TEXT,
                min_lat REAL NOT NULL,
                min_lon REAL NOT NULL,
                max_lat REAL NOT NULL,
                max_lon REAL NOT NULL,
                zoom INTEGER NOT NULL,
                detection_count INTEGER DEFAULT 0,
                vegetation_count INTEGER DEFAULT 0,
                water_count INTEGER DEFAULT 0,
                road_count INTEGER DEFAULT 0,
                built_up_count INTEGER DEFAULT 0,
                vegetation_pct REAL DEFAULT 0.0,
                geojson_current TEXT,
                geojson_past TEXT,
                image_width INTEGER DEFAULT 0,
                image_height INTEGER DEFAULT 0,
                tile_count INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS temporal_analyses (
                id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                detection_current INTEGER DEFAULT 0,
                detection_past INTEGER DEFAULT 0,
                detection_delta INTEGER DEFAULT 0,
                detection_growth_pct REAL DEFAULT 0.0,
                concrete_expansion_sqm REAL DEFAULT 0.0,
                concrete_growth_pct REAL DEFAULT 0.0,
                vegetation_current_pct REAL DEFAULT 0.0,
                vegetation_past_pct REAL DEFAULT 0.0,
                vegetation_change_pct REAL DEFAULT 0.0,
                metrics_json TEXT,
                FOREIGN KEY (scan_id) REFERENCES scan_results(id)
            );

            CREATE TABLE IF NOT EXISTS chat_logs (
                id TEXT PRIMARY KEY,
                scan_id TEXT,
                created_at TEXT NOT NULL,
                user_id TEXT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                evidence_ids TEXT,
                confidence TEXT,
                data_source TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_scans_bbox ON scan_results(min_lat, min_lon, max_lat, max_lon);
            CREATE INDEX IF NOT EXISTS idx_temporal_scan ON temporal_analyses(scan_id);
            CREATE INDEX IF NOT EXISTS idx_chat_scan ON chat_logs(scan_id);
        """)
        await db.commit()
    logger.info("Database tables initialized.")


async def save_scan_result(scan_data: dict) -> str:
    """Save a scan result to the database. Returns the scan ID."""
    import uuid
    scan_id = scan_data.get("id", str(uuid.uuid4()))
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(str(_get_db_path())) as db:
        await db.execute(
            """INSERT OR REPLACE INTO scan_results
               (id, created_at, user_id, min_lat, min_lon, max_lat, max_lon, zoom,
                detection_count, vegetation_count, water_count, road_count, built_up_count,
                vegetation_pct, geojson_current, geojson_past, image_width, image_height, tile_count)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                scan_id, now,
                scan_data.get("user_id"),
                scan_data.get("min_lat", 0), scan_data.get("min_lon", 0),
                scan_data.get("max_lat", 0), scan_data.get("max_lon", 0),
                scan_data.get("zoom", 0),
                scan_data.get("detection_count", 0),
                scan_data.get("vegetation_count", 0),
                scan_data.get("water_count", 0),
                scan_data.get("road_count", 0),
                scan_data.get("built_up_count", 0),
                scan_data.get("vegetation_pct", 0.0),
                json.dumps(scan_data.get("geojson_current")),
                json.dumps(scan_data.get("geojson_past")),
                scan_data.get("image_width", 0),
                scan_data.get("image_height", 0),
                scan_data.get("tile_count", 0),
            ),
        )
        await db.commit()
    return scan_id


async def save_temporal_analysis(temporal_data: dict) -> str:
    """Save temporal analysis metrics."""
    import uuid
    analysis_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    det = temporal_data.get("detections", {})
    built = temporal_data.get("built_up_areas", {})
    veg = temporal_data.get("vegetation", {})

    async with aiosqlite.connect(str(_get_db_path())) as db:
        await db.execute(
            """INSERT INTO temporal_analyses
               (id, scan_id, created_at, detection_current, detection_past,
                detection_delta, detection_growth_pct, concrete_expansion_sqm,
                concrete_growth_pct, vegetation_current_pct, vegetation_past_pct,
                vegetation_change_pct, metrics_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                analysis_id,
                temporal_data.get("scan_id", ""),
                now,
                det.get("current_count", 0),
                det.get("past_count", 0),
                det.get("net_change", 0),
                det.get("growth_percentage", 0.0),
                built.get("concrete_expansion_sqm", 0.0),
                built.get("concrete_growth_percentage", 0.0),
                veg.get("current_coverage_pct", 0.0),
                veg.get("past_coverage_pct", 0.0),
                veg.get("vegetation_change_pct", 0.0),
                json.dumps(temporal_data),
            ),
        )
        await db.commit()
    return analysis_id


async def save_chat_log(chat_data: dict) -> str:
    """Save a chat interaction."""
    import uuid
    chat_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    async with aiosqlite.connect(str(_get_db_path())) as db:
        await db.execute(
            """INSERT INTO chat_logs
               (id, scan_id, created_at, user_id, question, answer,
                evidence_ids, confidence, data_source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                chat_id,
                chat_data.get("scan_id"),
                now,
                chat_data.get("user_id"),
                chat_data.get("question", ""),
                chat_data.get("answer", ""),
                json.dumps(chat_data.get("evidence_ids", [])),
                chat_data.get("confidence", "none"),
                chat_data.get("data_source", ""),
            ),
        )
        await db.commit()
    return chat_id


async def get_scan_result(scan_id: str) -> Optional[dict]:
    """Retrieve a scan result by ID."""
    async with aiosqlite.connect(str(_get_db_path())) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM scan_results WHERE id = ?", (scan_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)


async def get_latest_scan_for_bbox(
    min_lat: float, min_lon: float, max_lat: float, max_lon: float
) -> Optional[dict]:
    """Get the most recent scan overlapping the given bounding box."""
    async with aiosqlite.connect(str(_get_db_path())) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """SELECT * FROM scan_results
               WHERE min_lat <= ? AND max_lat >= ? AND min_lon <= ? AND max_lon >= ?
               ORDER BY created_at DESC LIMIT 1""",
            (max_lat, min_lat, max_lon, min_lon),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return dict(row)
