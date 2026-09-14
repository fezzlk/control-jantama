from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CONTROL_JANTAMA_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    user_data_dir: Path = Path("data/user_data_dir")
    templates_dir: Path = Path("assets/templates")
    db_path: Path = Path("data/replay_urls.sqlite3")

    share_icon_template: str = "share_icon.png"
    dialog_marker_template: str = "dialog_marker.png"
    copy_button_template: str | None = None

    match_threshold: float = 0.85
    url_host_allowlist: str = "maj-soul.com,yo-star.com"
    dialog_appear_timeout_seconds: float = 10.0

    viewport_width: int = 1280
    viewport_height: int = 800

    start_url: str | None = None

    def template_path(self, filename: str) -> Path:
        return self.templates_dir / filename

    @property
    def url_host_allowlist_entries(self) -> list[str]:
        return [entry.strip() for entry in self.url_host_allowlist.split(",") if entry.strip()]


settings = Settings()
