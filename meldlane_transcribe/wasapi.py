"""Windows WASAPI loopback через pyaudiowpatch — системный звук из коробки,
с ЛЮБОГО устройства вывода (динамики, наушники, Bluetooth), без Stereo Mix
и без VB-Cable.

Optional: pyaudiowpatch — Windows-only пакет (объявлен в pyproject с
маркером `sys_platform == "win32"`). Если не установлен или не Windows —
is_available() возвращает False, capture.py откатывается на именованный
автодетект (Stereo Mix / BlackHole через sounddevice).

Проверено вживую: захват дефолтного вывода поймал системный звук
(проигранный Windows-сигнал), сигнал реальный (не тишина).
"""
import sys
import time
from pathlib import Path

import numpy as np

from .audio_utils import resample_to_16k


def is_available() -> bool:
    if sys.platform != "win32":
        return False
    try:
        import pyaudiowpatch  # noqa: F401
    except ImportError:
        return False
    return True


def record_loopback(max_seconds: float, flag: Path) -> np.ndarray:
    """Пишет loopback дефолтного устройства вывода до max_seconds или флага.
    Возвращает 16kHz mono int16 — тот же формат, что и остальные источники.
    """
    import pyaudiowpatch as pyaudio

    p = pyaudio.PyAudio()
    frames: list[bytes] = []
    try:
        device = p.get_default_wasapi_loopback()
        rate = int(device["defaultSampleRate"])
        channels = device["maxInputChannels"] or 1

        def callback(in_data, frame_count, time_info, status):
            frames.append(in_data)
            return (None, pyaudio.paContinue)

        stream = p.open(
            format=pyaudio.paInt16, channels=channels, rate=rate, input=True,
            input_device_index=device["index"], stream_callback=callback,
        )
        stream.start_stream()
        started = time.monotonic()
        while time.monotonic() - started < max_seconds:
            if flag.exists():
                break
            time.sleep(0.5)
        stream.stop_stream()
        stream.close()
    finally:
        p.terminate()

    raw = b"".join(frames)
    arr = (
        np.frombuffer(raw, dtype=np.int16).reshape(-1, channels)
        if raw
        else np.zeros((0, channels), dtype=np.int16)
    )
    return resample_to_16k(arr, rate)
