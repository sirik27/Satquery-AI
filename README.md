# DrishtiAI / SatQuery AI 🛰️

> **Autonomous Full-Stack Geospatial Intelligence & Temporal Change Analysis System**

DrishtiAI is a production-ready, dual-OS compatible (macOS & Windows) satellite intelligence platform. It processes real multi-spectral GeoTIFF raster imagery in real time to compute land cover, detect physical objects, perform temporal split-screen change detection, and answer questions grounded strictly in computed pixel and vector evidence.

---

## 🌟 Key Features

- **Zero Mock Data Policy**: Every building count, road segment, vegetation index (NDVI), water body area, and percentage change is calculated live at runtime from raw raster pixels and vector geometries using `rasterio`, `shapely`, `pyproj`, and `opencv-python`.
- **Live Map Explorer**: Leaflet-powered interactive map with bounding box scanner, GeoJSON feature overlays, evidence highlighting, and smooth fly-to animations.
- **Temporal Split-Screen (Time Travel)**: Interactive side-by-side or sliding comparison of multi-temporal satellite scans with automatic change vector computation.
- **Grounded AI Chatbot**: Natural language query engine strictly grounded in spatial evidence. Clickable evidence chips inside chat responses highlight exact target geometries on the live map.
- **Growth HUD & Metric Cards**: Real-time metric cards showing object counts, temporal deltas, and land-cover breakdown with smooth animations.
- **Export Engine**: One-click generation of audit-ready executive PDF reports with embedded map viewports, structured data tables, and evidence logs.
- **Dual-OS & Multi-Platform**: Fully cross-platform launcher (`run_dev.py`) supporting Windows and macOS natively.

---

## 🏗️ Architecture

```
satqueryAI/
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Environment & app configuration
│   ├── auth/                # Firebase Bearer token auth middleware
│   ├── database/            # SQLite metadata database
│   ├── engines/
│   │   ├── raster_engine.py  # Core GeoTIFF NDVI/MNDWI/vector analysis
│   │   ├── yolo_detector.py  # Object detection engine
│   │   └── temporal_engine.py# Split-screen time-series change analysis
│   ├── services/
│   │   ├── grounded_chat.py  # Spatial-grounded chat engine
│   │   └── report_generator.py # Executive PDF report generator
│   └── routers/             # API routes (/api/scan, /api/temporal, /api/chat, /api/export)
├── frontend/
│   ├── src/
│   │   ├── components/      # LiveMapExplorer, GroundedChatbot, GrowthHUD, FileUploader
│   │   ├── context/         # AuthContext with Firebase integration
│   │   ├── api/             # Axios API client with token interceptor
│   │   └── index.css        # Navy/Slate dynamic design system
│   ├── package.json
│   └── vite.config.js
├── run_dev.py               # Cross-platform zero-config launcher
└── requirements.txt
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+

### Running the Application

Simply execute the unified launcher script:
```bash
python run_dev.py
```

This single command will:
1. Create and configure the Python virtual environment (`venv`)
2. Install all required backend dependencies
3. Install frontend dependencies
4. Launch both the FastAPI backend (`http://localhost:8000`) and Vite frontend (`http://localhost:5173`)

---

## 🔒 Security & Firebase Setup

Firebase configuration is managed via standard environment variables in `.env` and `frontend/.env`. Authentication tokens are automatically verified on every backend API call.
