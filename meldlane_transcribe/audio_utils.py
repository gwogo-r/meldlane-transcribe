"""Общий ресемплинг для всех источников захвата (sounddevice, WASAPI loopback)."""
import numpy as np
from scipy.signal import resample_poly

SAMPLE_RATE = 16_000  # целевая частота для Whisper


def resample_to_16k(frames: np.ndarray, native_rate: int) -> np.ndarray:
    """native_rate Hz, любое число каналов -> SAMPLE_RATE Hz mono int16."""
    if frames.shape[1] > 1:
        frames = frames.mean(axis=1, keepdims=True).astype(np.int16)
    if native_rate == SAMPLE_RATE:
        return frames
    resampled = resample_poly(frames[:, 0].astype(np.float64), SAMPLE_RATE, native_rate)
    return np.clip(resampled, -32768, 32767).astype(np.int16).reshape(-1, 1)
