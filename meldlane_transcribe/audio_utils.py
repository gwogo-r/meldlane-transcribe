"""Общий ресемплинг для всех источников захвата (sounddevice, WASAPI loopback)."""
import numpy as np
from scipy.signal import resample_poly

SAMPLE_RATE = 16_000  # целевая частота для Whisper

# Обнаружено вживую (Meldlane, 2026-07-22): встроенный микрофонный массив
# ноутбука пишет сырой сигнал в ~15 раз тише системного звука (RMS ~200 из
# 32767) — собеседника это не касается, звонилка сама усиливает микрофон на
# лету, но наш raw-захват идёт ДО этого усиления. Whisper на таком тихом
# сигнале не распознаёт речь, а галлюцинирует повторяющиеся фразы-заглушки.
# Это не зависит от того, насколько громко говорит человек, — это сырой gain
# конкретного аудио-девайса. Нормализация ниже чинит это на уровне кода, не
# советом «покрути громкость в настройках Windows».
_TARGET_PEAK_FRACTION = 0.85
_MAX_GAIN = 20.0


def normalize_audio(frames: np.ndarray) -> np.ndarray:
    """Приводит пиковую амплитуду int16-сигнала к целевому уровню.

    max_gain ограничивает усиление, чтобы почти полная тишина (шумовой пол)
    не раздувалась в громкий шум — только реальный сигнал ниже целевого пика
    усиливается, и не более чем в 20 раз.
    """
    if frames.size == 0:
        return frames
    peak = int(np.abs(frames).max())
    if peak == 0:
        return frames
    gain = min((_TARGET_PEAK_FRACTION * 32767) / peak, _MAX_GAIN)
    return np.clip(frames.astype(np.float64) * gain, -32768, 32767).astype(np.int16)


def resample_to_16k(frames: np.ndarray, native_rate: int) -> np.ndarray:
    """native_rate Hz, любое число каналов -> SAMPLE_RATE Hz mono int16, нормализовано по амплитуде.

    Единая точка выхода для обоих путей захвата (mic через sounddevice,
    system audio через WASAPI loopback) — normalize_audio() применяется тут
    один раз, а не дублируется в capture.py/wasapi.py.
    """
    if frames.shape[1] > 1:
        frames = frames.mean(axis=1, keepdims=True).astype(np.int16)
    if native_rate != SAMPLE_RATE:
        resampled = resample_poly(frames[:, 0].astype(np.float64), SAMPLE_RATE, native_rate)
        frames = np.clip(resampled, -32768, 32767).astype(np.int16).reshape(-1, 1)
    return normalize_audio(frames)
