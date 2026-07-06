import json
from datetime import datetime
from pathlib import Path

from .models import Transcript


def create_session_dir(base: Path) -> Path:
    d = base / datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_transcript(session_dir: Path, transcript: Transcript) -> Path:
    """Сохраняет и JSON (машинный контракт), и .txt рядом (для чтения глазами)."""
    path = session_dir / "transcript.json"
    path.write_text(
        json.dumps(transcript.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    save_transcript_txt(session_dir, transcript)
    return path


def save_transcript_txt(session_dir: Path, transcript: Transcript) -> Path:
    path = session_dir / "transcript.txt"
    lines = []
    for s in transcript.segments:
        mm, ss = divmod(int(s.start), 60)
        who = f" {s.speaker}" if s.speaker else ""
        lines.append(f"[{mm:02d}:{ss:02d}{who}] {s.text}")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def cleanup_audio(session_dir: Path, keep_audio: bool) -> None:
    """Временные WAV-дорожки удаляются после транскрибации, если не попросили оставить."""
    if keep_audio:
        return
    for wav in session_dir.glob("*.wav"):
        wav.unlink(missing_ok=True)
