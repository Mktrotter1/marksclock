"""Application configuration loaded from environment / .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Settings:
    host: str = "0.0.0.0"
    port: int = 8080
    default_timezone: str = "America/New_York"
    # For sunrise/sunset — lat/lon of home location
    home_lat: float | None = None
    home_lon: float | None = None
    # Persistence
    state_dir: Path = field(default_factory=lambda: Path.home() / ".config" / "marksclock")

    @classmethod
    def from_env(cls) -> Settings:
        s = cls(
            host=os.getenv("MARKSCLOCK_HOST", "0.0.0.0"),
            port=int(os.getenv("MARKSCLOCK_PORT", "8080")),
            default_timezone=os.getenv("MARKSCLOCK_TZ", "America/New_York"),
        )
        lat = os.getenv("MARKSCLOCK_LAT")
        lon = os.getenv("MARKSCLOCK_LON")
        if lat and lon:
            s.home_lat = float(lat)
            s.home_lon = float(lon)
        state_dir = os.getenv("MARKSCLOCK_STATE_DIR")
        if state_dir:
            s.state_dir = Path(state_dir)
        return s


settings = Settings.from_env()
