"""
DrishtiAI Configuration — Pydantic Settings with cross-platform defaults.
All paths use pathlib.Path for Windows/macOS compatibility.
"""

import sys
import torch
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


def detect_device() -> str:
    """Select optimal compute device: MPS (Apple Silicon) > CUDA (NVIDIA) > CPU."""
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    allowed_origins: str = "http://localhost:5173,http://localhost:3000,https://*.vercel.app"

    # Firebase
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""

    # Database
    database_url: str = "sqlite:///./data/drishti.db"

    # YOLO
    yolo_model_path: str = "yolov8n.pt"

    # Directories
    tile_cache_dir: str = "./data/tile_cache"
    upload_dir: str = "./data/uploads"

    # Development
    dev_mode: bool = True

    # Computed
    @property
    def device(self) -> str:
        return detect_device()

    @property
    def tile_cache_path(self) -> Path:
        p = Path(self.tile_cache_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
