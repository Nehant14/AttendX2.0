"""Application configuration loaded from environment / .env file."""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    APP_ENV: str = "dev"
    SECRET_KEY: str = "dev-secret-change-me"
    AUTH_ENABLED: bool = True
    ADMIN_EMAIL: str = "admin@example.com"
    ADMIN_PASSWORD: str = "nehant123"
    TOKEN_EXPIRE_MINUTES: int = 720

    # Database / Storage
    DATABASE_URL: str = "sqlite:///./data/attendance.sqlite3"
    DATA_DIR: Path = Path("./data")
    MAX_UPLOAD_MB: int = 25

    # Detector
    DETECTOR: str = "pretrained"
    FINETUNED_MODEL_PATH: Path = Path("models/face_ft_best.onnx")
    INSIGHTFACE_MODEL: str = "scrfd_34gf_r100"
    INSIGHTFACE_HOME: str = "~/.insightface"

    # Detection
    DET_SIZE: int = 640          # SCRFD-34GF has a fixed 640×640 input in the ONNX graph
    DET_CONF_MIN: float = 0.40
    MIN_FACE_PX: int = 40

    # Matching
    SIM_ACCEPT: float = 0.45
    SIM_REVIEW_MIN: float = 0.35
    MARGIN_MIN: float = 0.05

    # Enrollment
    ENROLL_MIN_PHOTOS: int = 3
    ENROLL_MAX_PHOTOS: int = 15
    ENROLL_MIN_FACE_PX: int = 80
    ENROLL_MIN_DET_SCORE: float = 0.60
    ENROLL_MIN_BLUR_VAR: float = 60.0
    ENROLL_DUPLICATE_SIM: float = 0.60

    # Optional
    TILING: bool = False
    # Testing / ops: skip loading ML models at startup (used by the test-suite)
    SKIP_MODEL_LOAD: bool = False
    CORS_ORIGINS: str = "http://localhost:5173"

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV.lower() == "prod"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def insightface_home_resolved(self) -> str:
        return str(Path(self.INSIGHTFACE_HOME).expanduser())


settings = Settings()
