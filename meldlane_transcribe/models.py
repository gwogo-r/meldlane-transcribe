"""Контракт Transcript — общая JSON-схема между сервисами Meldlane. Не ломать."""
from datetime import datetime, timezone

from pydantic import BaseModel, Field


class Segment(BaseModel):
    start: float
    end: float
    # "me" (mic-дорожка) | "others" (system-дорожка) | "spk_N" (pyannote) | None (неизвестно)
    speaker: str | None = None
    text: str


class SourceInfo(BaseModel):
    type: str  # "live" | "file"
    path: str | None = None


class Transcript(BaseModel):
    meeting_id: str
    lang: str = ""
    duration_sec: float = 0.0
    source: SourceInfo
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    segments: list[Segment] = Field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n".join(s.text for s in self.segments)


def merge_tracks(*tracks: list[Segment]) -> list[Segment]:
    """Сливает сегменты нескольких дорожек (me/others) в одну ленту по времени начала."""
    merged: list[Segment] = []
    for track in tracks:
        merged.extend(track)
    return sorted(merged, key=lambda s: s.start)
