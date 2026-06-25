from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class Chapter:
    title: str
    text: str = ""
    audio_path: Optional[Path] = None
    duration_ms: int = 0


@dataclass
class BookMetadata:
    title: str
    author: str = "Unknown"
    narrator: str = ""
    year: str = ""
    cover_image: Optional[Path] = None
    description: str = ""
