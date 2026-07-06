"""Живой захват: mic + system audio РАЗДЕЛЬНЫМИ дорожками (mic.wav / system.wav).

Дорожки не миксуются — это даёт диаризацию «me / others» бесплатно, без ML:
всё с микрофона — «я», всё с системного захвата — «собеседники».

Системный звук — каскад стратегий (первая доступная побеждает):
1. WASAPI loopback (Windows, pyaudiowpatch) — работает из коробки с ЛЮБЫМ
   устройством вывода, наушники/Bluetooth не проблема. См. wasapi.py.
2. Именованный loopback-девайс через sounddevice — Stereo Mix/VB-Cable
   (Windows, если WASAPI недоступен) или BlackHole (macOS).
3. Ничего не найдено — пишем только микрофон.

Выстраданные на Windows решения (не терять при рефакторинге):
- callback-API, не blocking read: WDM-KS устройства (Stereo Mix) падают на
  блокирующем чтении с PaErrorCode -9999;
- запись на НАТИВНОЙ частоте устройства (Stereo Mix — 48kHz) с ресемплингом
  до 16kHz: открытие потока сразу на 16000 падает с "Invalid device";
- device=None разрешать через sd.default.device: sd.query_devices(None)
  возвращает список ВСЕХ устройств, а не дефолтное;
- graceful stop через файл-флаг: остановка из другого процесса сохраняет
  накопленное аудио вместо потери всей записи.
"""
import time
import wave
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd

from . import config
from .audio_utils import SAMPLE_RATE, resample_to_16k

MAX_SECONDS_DEFAULT = 4 * 3600

# известные имена loopback-устройств для автодетекта (fallback-путь, без WASAPI)
LOOPBACK_NAME_HINTS = ["стерео микшер", "stereo mix", "what u hear", "cable output", "blackhole", "loopback"]


def stop_flag_path(base_dir: Path) -> Path:
    return base_dir / ".capture_stop"


def request_stop(base_dir: Path) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    stop_flag_path(base_dir).touch()


def find_device(name_hint: str | None, kind: str = "input") -> int | None:
    """Ищет устройство по подстроке имени. None -> системное дефолтное."""
    if not name_hint:
        return None
    for i, d in enumerate(sd.query_devices()):
        channels = d["max_input_channels"] if kind == "input" else d["max_output_channels"]
        if channels > 0 and name_hint.lower() in d["name"].lower():
            return i
    raise ValueError(f"аудио-устройство не найдено: {name_hint!r}")


def autodetect_loopback() -> int | None:
    """Ищет именованное loopback-устройство (Stereo Mix / VB-Cable / BlackHole)
    через sounddevice — fallback-путь, когда WASAPI loopback недоступен."""
    explicit = config.system_device()
    if explicit:
        return find_device(explicit, "input")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0 and any(h in d["name"].lower() for h in LOOPBACK_NAME_HINTS):
            return i
    return None


def _record_stream(device: int | None, max_seconds: float, flag: Path) -> np.ndarray:
    resolved = device if device is not None else sd.default.device[0]
    info = sd.query_devices(resolved)
    native_rate = int(info["default_samplerate"])
    channels = min(info["max_input_channels"], 2) or 1

    frames: list[np.ndarray] = []

    def callback(indata, frame_count, time_info, status):
        frames.append(indata.copy())

    started = time.monotonic()
    with sd.InputStream(samplerate=native_rate, channels=channels, dtype="int16", device=resolved, callback=callback):
        while time.monotonic() - started < max_seconds:
            if flag.exists():
                break
            time.sleep(0.5)

    raw = np.concatenate(frames, axis=0) if frames else np.zeros((0, channels), dtype="int16")
    return resample_to_16k(raw, native_rate)


def system_track_strategy() -> tuple[str, Callable[[float, Path], np.ndarray]] | None:
    """Выбирает стратегию захвата системного звука. Возвращает (имя, функция) или None."""
    from . import wasapi

    if wasapi.is_available():
        return "wasapi-loopback", wasapi.record_loopback

    idx = autodetect_loopback()
    if idx is not None:
        return "named-device", lambda max_seconds, flag: _record_stream(idx, max_seconds, flag)

    return None


def _write_wav(path: Path, frames: np.ndarray) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # int16
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(frames.tobytes())


def record_tracks(session_dir: Path, max_seconds: float = MAX_SECONDS_DEFAULT) -> dict[str, Path]:
    """Пишет дорожки до max_seconds или стоп-флага. Возвращает {"me": mic.wav, "others": system.wav}.

    "others" присутствует, только если найдена рабочая стратегия захвата системного
    звука (см. system_track_strategy). Стоп-флаг живёт в родительской папке сессий
    (outputs/.capture_stop) — его ставит `mtranscribe stop` из другого процесса.
    """
    flag = stop_flag_path(session_dir.parent)
    flag.unlink(missing_ok=True)

    mic_idx = find_device(config.mic_device(), "input")
    strategy = system_track_strategy()
    session_dir.mkdir(parents=True, exist_ok=True)

    tracks: dict[str, Path] = {}
    if strategy is None:
        frames = _record_stream(mic_idx, max_seconds, flag)
        tracks["me"] = session_dir / "mic.wav"
        _write_wav(tracks["me"], frames)
    else:
        _, record_system = strategy
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            mic_future = pool.submit(_record_stream, mic_idx, max_seconds, flag)
            sys_future = pool.submit(record_system, max_seconds, flag)
            mic_frames = mic_future.result()
            sys_frames = sys_future.result()

        tracks["me"] = session_dir / "mic.wav"
        tracks["others"] = session_dir / "system.wav"
        _write_wav(tracks["me"], mic_frames)
        _write_wav(tracks["others"], sys_frames)

    flag.unlink(missing_ok=True)
    return tracks
