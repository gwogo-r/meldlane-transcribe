from pathlib import Path

from faster_whisper import WhisperModel

from . import config
from .models import Segment

# faster-whisper декодирует аудио сам через PyAV — внешний ffmpeg не нужен
AUDIO_FORMATS = {".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac", ".wma", ".opus"}
# видеоконтейнеры PyAV тоже открывает в большинстве случаев (берёт аудиодорожку)
VIDEO_FORMATS = {".mp4", ".mkv", ".webm", ".mov", ".avi", ".wmv", ".mpeg", ".mpg", ".m4v", ".flv"}
SUPPORTED_FORMATS = AUDIO_FORMATS | VIDEO_FORMATS

_model: WhisperModel | None = None  # ленивая загрузка — модель нужна только при транскрибации


def _get_model() -> WhisperModel:
    global _model
    if _model is None:
        # CTranslate2: в разы быстрее оригинального openai-whisper на CPU, не тянет torch
        _model = WhisperModel(config.whisper_model(), device="cpu", compute_type="int8")
    return _model


def transcribe_file(path: Path, speaker: str | None = None) -> tuple[list[Segment], str, float]:
    """Файл -> (сегменты, язык, длительность). speaker проставляется всем сегментам."""
    if path.suffix.lower() not in SUPPORTED_FORMATS:
        raise ValueError(
            f"формат {path.suffix!r} не поддерживается; аудио: {sorted(AUDIO_FORMATS)}, видео: {sorted(VIDEO_FORMATS)}"
        )
    segments_iter, info = _get_model().transcribe(str(path), language=config.language())
    segments = [
        Segment(start=s.start, end=s.end, speaker=speaker, text=s.text.strip())
        for s in segments_iter
    ]
    return segments, info.language or "", info.duration or 0.0
