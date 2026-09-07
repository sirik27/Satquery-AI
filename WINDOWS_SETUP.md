# DrishtiAI / SatQuery AI — Windows Local Setup & Presentation Guide 🛰️

> **Complete Zero-Config Setup Guide for Windows 10/11 Evaluators & Demonstrations**

---

## 🛠️ System Prerequisites

Ensure the Windows machine has the following installed before starting:

1. **Python 3.9, 3.10, or 3.11**
   - Download from [python.org](https://www.python.org/downloads/)
   - ⚠️ **CRITICAL**: During installation, check the box **"Add Python to PATH"**.
2. **Node.js 18 or 20 (LTS)**
   - Download from [nodejs.org](https://nodejs.org/)
3. **Git for Windows**
   - Download from [git-scm.com](https://git-scm.com/)

---

## 🚀 Step-by-Step Installation Guide

### Step 1: Clone the Repository
Open **Command Prompt (cmd)** or **PowerShell** and run:

```cmd
git clone https://github.com/sirik27/Satquery-AI.git
cd Satquery-AI
```

---

### Step 2: One-Click Automated Launch (Recommended)
We built a cross-platform zero-config launcher script (`run_dev.py`) that automates virtual environment creation, pip installation, frontend npm install, and server execution.

Run:
```cmd
python run_dev.py
```

#### What `run_dev.py` automatically does:
1. Creates a Python virtual environment (`venv`).
2. Installs/Upgrades `pip`.
3. Installs backend dependencies from `requirements.txt` (FastAPI, PyTorch, Ultralytics, Rasterio, OpenCV, Shapely).
4. Installs frontend npm packages (`React`, `Vite`, `Leaflet`, `Lucide`, `Recharts`).
5. Launches:
   - **Backend API**: `http://localhost:8000`
   - **Frontend UI**: `http://localhost:5173`

---

## ⚙️ Manual Setup Option (If preferred)

If you prefer installing dependencies manually step-by-step:

### 1. Backend Setup:
```cmd
:: Create and activate virtual environment
python -m venv venv
venv\Scripts\activate

:: Install Python packages
pip install --upgrade pip
pip install -r requirements.txt

:: Start FastAPI backend
python run_dev.py
```

### 2. Frontend Setup (in a second terminal):
```cmd
cd frontend
npm install
npm run dev
```

---

## 💻 Accessing the Application

Once launched, open Google Chrome or Microsoft Edge and visit:
👉 **`http://localhost:5173`**

---

## 🎯 Evaluator Demo Script (Showcasing Key Features)

Here is a step-by-step walkthrough to impress evaluators during a live demo:

### 1. Sign In & Authentication (Zero-Friction Dev Mode)
- Click **"Sign In"** or **"Sign Up"**.
- Enter any email (e.g. `evaluator@satquery.ai`) and password.
- The app instantly logs in and opens the **Satellite Intelligence Dashboard**.

### 2. Live Satellite Viewport Scanner (Zero Mock Data)
- Pan and zoom the Leaflet map over any area (e.g. Hyderabad, London, New York).
- Click **"Scan Viewport"** in the bottom control bar.
- Point out to evaluators:
  - **Vegetation %** calculated live via GLI (Green Leaf Index).
  - **Water Bodies & Built-up Areas** vectorized in real-time.
  - **Object Detections** via YOLOv8 model inference.

### 3. Interactive Point Coordinates Inspector
- Click anywhere on the satellite map.
- Point out the **floating coordinate badge** displaying exact WGS84 coordinates (e.g., `📍 17.418810°N, 78.343500°E`).

### 4. Temporal Split-Screen (Time Travel)
- Click **"Time Travel"** in the control bar.
- Click **"Show 2021"** to enable the split-screen slider.
- Show evaluators historical vs. current satellite imagery and automatic change vector computation.

### 5. Grounded AI Chatbot
- Open the **Chat Drawer** on the right side.
- Type: *"How many buildings and vegetation areas were detected?"*
- Click an **Evidence Chip** in the chatbot's response — the map will automatically **fly to and highlight** the exact polygon feature on the map!

### 6. Spatial Analytics Dashboard
- Click **"Analytics"** in the left sidebar.
- Show the interactive **Land Cover Distribution Pie Chart** and **Vector Feature Counts Bar Chart**.

### 7. Executive PDF Export
- Click **"Export PDF"** in the top navigation bar.
- Show the generated audit-ready PDF report containing embedded map viewports, metric tables, and spatial evidence logs.

---

## ❓ Troubleshooting Common Windows Issues

1. **`'python' is not recognized as an internal or external command`**:
   - Re-install Python and check **"Add Python to PATH"** on the first installer screen.
2. **`Execution of scripts is disabled on this system` (PowerShell)**:
   - Run PowerShell as Administrator and execute: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
3. **Port 8000 or 5173 in use**:
   - Open Command Prompt and run: `taskkill /F /IM python.exe` and `taskkill /F /IM node.exe`.
