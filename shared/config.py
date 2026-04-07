from pathlib import Path
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root (parent of `shared/`); avoids missing or wrong `.env` when cwd is not the project root.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/buffet"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    video_source: str | None = None
    worker_camera_id: str | None = None
    target_fps: float = 5.0
    serve_dwell_seconds: float = 2.0
    yolo_weights: str = "yolov8n.pt"
    yolo_person_class_id: int = 0
    yolo_plate_class_ids: str = "45"
    # When True and zones exist: crop to union of zone AABBs (+ padding) before YOLO; map boxes back to full frame.
    yolo_roi_crop: bool = True
    yolo_roi_padding_frac: float = 0.15
    classifier_checkpoint: str | None = None
    classifier_labels: str = "rice,beans,salad,chicken"
    classification_threshold: float = 0.5
    worker_max_frames: int | None = None
    require_person_near_plate: bool = True
    # Phase 3 calibration / Phase 6 debug: off | imshow (local OpenCV window with zones + boxes)
    worker_preview: Literal["off", "imshow"] = "off"
    # Reserved for future MJPEG preview; unused when worker_preview=imshow
    worker_preview_port: int = 8080

    @field_validator("worker_preview", mode="before")
    @classmethod
    def normalize_worker_preview(cls, v: str | None) -> str:
        if v is None or (isinstance(v, str) and not str(v).strip()):
            return "off"
        s = str(v).strip().lower()
        if s not in ("off", "imshow"):
            raise ValueError("WORKER_PREVIEW must be 'off' or 'imshow'")
        return s

    @field_validator("yolo_plate_class_ids", mode="before")
    @classmethod
    def strip_plate_ids(cls, v: str) -> str:
        if isinstance(v, str):
            return v
        return ",".join(str(x) for x in v)

    def plate_class_ids_list(self) -> list[int]:
        return [int(x.strip()) for x in self.yolo_plate_class_ids.split(",") if x.strip()]

    def classifier_label_list(self) -> list[str]:
        return [x.strip() for x in self.classifier_labels.split(",") if x.strip()]


def get_settings() -> Settings:
    """Load settings from the environment and repo `.env` (no cross-call cache).

    Each call returns a new ``Settings`` instance so a fresh process run always
    reflects the current file and env vars. OS environment variables still override
    values from ``.env`` (pydantic-settings default).
    """
    return Settings()
