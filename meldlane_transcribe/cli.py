import sys
import uuid
from pathlib import Path

import typer

# Windows-консоль часто в cp1251 — форсируем UTF-8, иначе кириллица падает
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

from . import config
from .models import SourceInfo, Transcript, merge_tracks

app = typer.Typer(
    add_completion=False,
    help="meldlane-transcribe — файл или живой звук (mic+system) в JSON-транскрипт с таймлайном и спикерами",
)


def _print_transcript(transcript: Transcript, path: Path) -> None:
    print(f"язык: {transcript.lang or '—'} · сегментов: {len(transcript.segments)} · {transcript.duration_sec:.0f} сек")
    for s in transcript.segments[:10]:
        who = s.speaker or "?"
        print(f"  [{s.start:7.1f}s {who:>6}] {s.text}")
    if len(transcript.segments) > 10:
        print(f"  ... и ещё {len(transcript.segments) - 10}")
    print(f"сохранено: {path} (+ {path.with_suffix('.txt').name} для чтения)")


@app.command("file")
def file_cmd(
    audio: Path = typer.Argument(..., help="аудио (mp3/wav/m4a/ogg/aac/...) или видео (mp4/mkv/webm/...)"),
):
    """Транскрибировать файл -> outputs/<время>/transcript.json."""
    from .sessions import create_session_dir, save_transcript
    from .transcriber import transcribe_file

    session = create_session_dir(config.outputs_dir())
    print(f"транскрибирую {audio} (модель {config.whisper_model()})...")
    segments, lang, duration = transcribe_file(audio)
    transcript = Transcript(
        meeting_id=uuid.uuid4().hex[:12],
        lang=lang,
        duration_sec=duration,
        source=SourceInfo(type="file", path=str(audio)),
        segments=segments,
    )
    path = save_transcript(session, transcript)
    _print_transcript(transcript, path)


@app.command("record")
def record_cmd(
    seconds: int | None = typer.Option(None, help="длительность; без флага — пишет, пока не вызовут `mtranscribe stop`"),
    keep_audio: bool = typer.Option(False, "--keep-audio", help="не удалять WAV-дорожки после транскрибации"),
):
    """Записать mic (+ system audio, если найден loopback) и сразу транскрибировать."""
    from .capture import MAX_SECONDS_DEFAULT, record_tracks, system_track_strategy
    from .sessions import cleanup_audio, create_session_dir, save_transcript
    from .transcriber import transcribe_file

    session = create_session_dir(config.outputs_dir())
    strategy = system_track_strategy()
    sys_label = {"wasapi-loopback": "WASAPI loopback", "named-device": "именованное устройство"}.get(
        strategy[0] if strategy else "", "нет — только микрофон"
    )
    print(f"запись{f' {seconds} сек' if seconds else ' (останови: mtranscribe stop)'}... "
          f"(mic: {config.mic_device() or 'default'}, system: {sys_label})")

    tracks = record_tracks(session, seconds or MAX_SECONDS_DEFAULT)
    print(f"записаны дорожки: {', '.join(tracks)}; транскрибирую...")

    all_segments, lang, duration = [], "", 0.0
    for speaker, wav in tracks.items():
        segments, track_lang, track_dur = transcribe_file(wav, speaker=speaker)
        all_segments.append(segments)
        lang = lang or track_lang
        duration = max(duration, track_dur)

    transcript = Transcript(
        meeting_id=uuid.uuid4().hex[:12],
        lang=lang,
        duration_sec=duration,
        source=SourceInfo(type="live"),
        segments=merge_tracks(*all_segments),
    )
    path = save_transcript(session, transcript)
    cleanup_audio(session, keep_audio)
    _print_transcript(transcript, path)


@app.command("stop")
def stop_cmd():
    """Остановить идущую запись из другого терминала — накопленное сохранится."""
    from .capture import request_stop

    request_stop(config.outputs_dir())
    print("сигнал остановки отправлен — запись сохранится и завершится в течение ~1 сек")


@app.command("doctor")
def doctor_cmd():
    """Диагностика: устройства, стратегия захвата, что делать, если системного звука нет."""
    import sounddevice as sd

    from .capture import LOOPBACK_NAME_HINTS, system_track_strategy

    print("входные аудио-устройства:")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            print(f"  {i:3} {d['name']}  ({int(d['default_samplerate'])} Hz)")

    default_in = sd.default.device[0]
    print(f"\nмикрофон по умолчанию: #{default_in} {sd.query_devices(default_in)['name']}")

    strategy = system_track_strategy()
    if strategy is not None:
        name, _ = strategy
        label = {
            "wasapi-loopback": "WASAPI loopback (любой вывод, без Stereo Mix/VB-Cable)",
            "named-device": "именованное loopback-устройство (Stereo Mix/VB-Cable/BlackHole)",
        }[name]
        print(f"системный звук: {label} — записывается дорожка «others»")
    else:
        print("системный звук: не найден — запись пойдёт только с микрофона.")
        if sys.platform == "win32":
            print("  Windows: установи pyaudiowpatch (pip install pyaudiowpatch) для WASAPI loopback,")
            print("  или включи «Стерео микшер» (Панель управления → Звук → Запись → ПКМ → Показать отключённые),")
            print("  или установи VB-Cable (vb-audio.com/Cable).")
        elif sys.platform == "darwin":
            print("  macOS: установи BlackHole одной командой: brew install blackhole-2ch")
        print(f"  именованный автодетект ищет: {', '.join(LOOPBACK_NAME_HINTS)} (или задай MTRANSCRIBE_SYSTEM_DEVICE)")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
