"""Application settings (read from environment / .env; every value has a default)."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Single login (JWT)
    SECRET_KEY: str = "dev-secret-change-me-0123456789abcdef"
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "nehant123"
    TOKEN_EXPIRE_MINUTES: int = 720

    # Storage
    DATABASE_URL: str = "sqlite:///./data/attendance.sqlite3"
    DATA_DIR: Path = Path("./data")

    # Detector: "pretrained" (InsightFace SCRFD) or "finetuned" (your YOLOv8-face ONNX)
    DETECTOR: str = "pretrained"
    FINETUNED_MODEL_PATH: Path = Path("models/face_ft_best.onnx")
    INSIGHTFACE_MODEL: str = "scrfd_34gf_r100"
    INSIGHTFACE_HOME: str = "~/.insightface"
    DET_CONF_MIN: float = 0.40

    # Matching: a face is a student if cosine similarity >= this
    SIM_THRESHOLD: float = 0.45

    @property
    def insightface_home_resolved(self) -> str:
        return str(Path(self.INSIGHTFACE_HOME).expanduser())


settings = Settings()
