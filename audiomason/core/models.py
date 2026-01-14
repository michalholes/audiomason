"""
Audiomason v2 – core.models
Definuje dátové modely pre audio spracovanie a pipeline.
"""

from __future__ import annotations
from typing import List, Optional, Literal
from pathlib import Path
from uuid import UUID, uuid4
from datetime import datetime
from pydantic import BaseModel, Field


class AudioTags(BaseModel):
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    narrator: Optional[str] = None
    year: Optional[int] = None
    genre: Optional[str] = None
    track_number: Optional[int] = None
    total_tracks: Optional[int] = None
    language: Optional[str] = None
    isbn: Optional[str] = None
    comment: Optional[str] = None


class CoverImage(BaseModel):
    source: Literal["file", "url", "generated"]
    path_or_url: str
    width: Optional[int] = None
    height: Optional[int] = None
    checksum: Optional[str] = None


class AudioTrack(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    path: Path
    duration: float
    bitrate: int
    channels: int
    sample_rate: int
    format: str
    tags: AudioTags
    cover: Optional[CoverImage] = None


class BookMetadata(BaseModel):
    title: str
    author: str
    narrator: Optional[str] = None
    language: Optional[str] = "en"
    isbn: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[int] = None
    description: Optional[str] = None
    cover: Optional[CoverImage] = None
    tags: List[AudioTags] = []


class ManifestEntry(BaseModel):
    path: Path
    type: Literal["audio", "cover", "meta", "other"]
    size: int
    checksum: Optional[str] = None


class Manifest(BaseModel):
    version: str = "1.0"
    entries: List[ManifestEntry]
    checksum: Optional[str] = None


class BookState(BaseModel):
    imported: bool = False
    validated: bool = False
    tagged: bool = False
    published: bool = False
    errors: List[str] = []


class BookPackage(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    root_path: Path
    tracks: List[AudioTrack]
    metadata: BookMetadata
    manifest: Manifest
    state: BookState


class ProcessingContext(BaseModel):
    package: BookPackage
    workspace: Path
    config: dict = {}
    temp_files: List[Path] = []
    logs: List[str] = []
    start_time: datetime = Field(default_factory=datetime.now)

    def log(self, message: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.logs.append(f"[{ts}] {message}")
