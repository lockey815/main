from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore", protected_namespaces=())

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    frontend_url: str = "http://localhost:5173"
    database_url: str = "sqlite:///./leuknet.db"

    # ---- auth (email + password accounts, as in the original LeukNet) ----
    secret_key: str = "change-me-in-production"
    token_hours: int = 12
    admin_email: str = ""      # if both are set, this account is created on startup
    admin_password: str = ""

    # ---- model files ----
    model_config_path: str = "model/config.json"
    model_weights_path: str = "model/model.weights.h5"
    model_metadata_path: str = "model/metadata.json"

    preprocess_mode: str = "resnet"  # resnet | rescale | none
    class_names: str = "blast,non_blast"
    blast_class_index: int = 0

    # ---- analysis ----
    tile_stride: int = 0  # 0 -> use the model input size
    max_image_side: int = 1536
    blast_prob_threshold: float = 0.5
    max_files_per_request: int = 8
    max_samples_per_session: int = 8
    max_upload_mb: int = 15
    max_pdf_pages: int = 4
    blur_threshold: float = 8.0          # variance of Laplacian below this -> "Unknown (blurred)"
    foreign_object_check: bool = True    # heuristic, see ml.py
    min_stain_fraction: float = 0.02     # whole-image stained pixels below this -> "Unknown (not a smear)"
    # Report rule: blasts above this -> "acute lymphoblastic leukemia", otherwise "chronic". 0 disables the rule.
    acute_blast_threshold: int = 15
    session_ttl_hours: int = 24

    # ---- optional Mistral summaries ----
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"
    mistral_timeout: float = 20.0

    # ---- verification page ----
    verify_show_full_details: bool = True  # False -> initials only

    @property
    def origins(self) -> list[str]:
        return [o.strip().rstrip("/") for o in self.cors_origins.split(",") if o.strip()]

    @property
    def class_list(self) -> list[str]:
        return [c.strip() for c in self.class_names.split(",") if c.strip()]

    def resolve(self, p: str) -> Path:
        path = Path(p)
        return path if path.is_absolute() else BASE_DIR / path


@lru_cache
def get_settings() -> Settings:
    return Settings()
