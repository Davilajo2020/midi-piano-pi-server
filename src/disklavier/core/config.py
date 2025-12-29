"""Configuration management for Disklavier Pi."""

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GeneralSettings(BaseModel):
    """General application settings."""
    device_name: str = "Disklavier Pi"
    log_level: str = "INFO"


class WebSettings(BaseModel):
    """Web server settings."""
    host: str = "0.0.0.0"
    port: int = 8080


class MIDISettings(BaseModel):
    """MIDI device settings."""
    device: str = "auto"
    channel: int = 0
    velocity_curve: str = "linear"


class SoundfontSettings(BaseModel):
    """Soundfont settings for FluidSynth."""
    path: str = "/opt/disklavier/soundfonts/general_montage.sf2"
    gain: float = 1.0


class AirPlayBroadcastSettings(BaseModel):
    """AirPlay broadcast settings."""
    enabled: bool = False  # Disabled by default due to ~2s AirPlay latency
    target: str = "auto"
    audio_delay_ms: int = 0  # Delay audio to sync with piano (0-2000ms)


class NetworkMIDISettings(BaseModel):
    """Network MIDI (RTP-MIDI) settings."""
    enabled: bool = True
    port: int = 5004


class UploadsSettings(BaseModel):
    """File upload settings."""
    directory: str = "/var/lib/disklavier/uploads"
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = Field(default_factory=lambda: [".mid", ".midi", ".kar"])


class CatalogSettings(BaseModel):
    """MIDI file catalog settings."""
    directories: list[str] = Field(default_factory=lambda: ["/var/lib/disklavier/catalog"])
    scan_subdirs: bool = True
    allowed_extensions: list[str] = Field(default_factory=lambda: [".mid", ".midi", ".kar"])


class Settings(BaseSettings):
    """Main application settings."""

    model_config = SettingsConfigDict(
        env_prefix="DISKLAVIER_",
        env_nested_delimiter="__",
    )

    general: GeneralSettings = Field(default_factory=GeneralSettings)
    web: WebSettings = Field(default_factory=WebSettings)
    midi: MIDISettings = Field(default_factory=MIDISettings)
    soundfont: SoundfontSettings = Field(default_factory=SoundfontSettings)
    airplay_broadcast: AirPlayBroadcastSettings = Field(default_factory=AirPlayBroadcastSettings)
    network_midi: NetworkMIDISettings = Field(default_factory=NetworkMIDISettings)
    uploads: UploadsSettings = Field(default_factory=UploadsSettings)
    catalog: CatalogSettings = Field(default_factory=CatalogSettings)

    @classmethod
    def from_yaml(cls, path: Path) -> "Settings":
        """Load settings from a YAML file."""
        if not path.exists():
            return cls()

        with open(path) as f:
            data = yaml.safe_load(f) or {}

        return cls(**data)


def find_config_file() -> Optional[Path]:
    """Find the configuration file in standard locations."""
    locations = [
        Path("/etc/disklavier/disklavier.yaml"),
        Path.home() / ".config" / "disklavier" / "disklavier.yaml",
        Path("config/disklavier.yaml"),
        Path("disklavier.yaml"),
    ]

    for path in locations:
        if path.exists():
            return path

    return None


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    config_path = find_config_file()

    if config_path:
        return Settings.from_yaml(config_path)

    return Settings()
