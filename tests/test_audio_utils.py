import numpy as np

from meldlane_transcribe.audio_utils import SAMPLE_RATE, normalize_audio, resample_to_16k


def test_normalize_audio_boosts_quiet_signal_to_target_peak():
    quiet = np.array([200, -150, 180, -190], dtype=np.int16).reshape(-1, 1)

    normalized = normalize_audio(quiet)

    assert np.abs(normalized).max() > np.abs(quiet).max() * 5
    assert np.abs(normalized).max() <= 32767


def test_normalize_audio_caps_gain_on_near_silence():
    almost_silent = np.array([2, -1, 1, -2], dtype=np.int16).reshape(-1, 1)

    normalized = normalize_audio(almost_silent)

    # gain is capped at 20x - shouldn't explode a near-zero signal to full scale
    assert np.abs(normalized).max() <= 2 * 20


def test_normalize_audio_pulls_clipping_signal_toward_target():
    loud = np.array([32767, -32768, 32767, -32768], dtype=np.int16).reshape(-1, 1)

    normalized = normalize_audio(loud)

    assert np.abs(normalized).max() < 32767


def test_normalize_audio_handles_silence_and_empty_without_crashing():
    silence = np.zeros((10, 1), dtype=np.int16)
    assert normalize_audio(silence).tolist() == silence.tolist()

    empty = np.zeros((0, 1), dtype=np.int16)
    assert normalize_audio(empty).size == 0


def test_resample_to_16k_changes_rate_and_normalizes():
    native_rate = 48_000
    quiet_tone = (np.sin(np.linspace(0, 40 * np.pi, native_rate)) * 300).astype(np.int16).reshape(-1, 1)

    result = resample_to_16k(quiet_tone, native_rate)

    assert result.shape[0] == round(len(quiet_tone) * SAMPLE_RATE / native_rate)
    assert np.abs(result).max() > 300 * 5
