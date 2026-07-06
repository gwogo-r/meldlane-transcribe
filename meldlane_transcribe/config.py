"""Настройки: env-переменные MTRANSCRIBE_* с разумными дефолтами, без обязательного конфига."""
import os
from pathlib import Path


def whisper_model() -> str:
    return os.getenv("MTRANSCRIBE_MODEL", "base")


def language() -> str | None:
    """None -> авто-детект языка (дефолт для публичного инструмента)."""
    return os.getenv("MTRANSCRIBE_LANGUAGE") or None


def mic_device() -> str | None:
    return os.getenv("MTRANSCRIBE_MIC_DEVICE") or None


def system_device() -> str | None:
    """Подстрока имени loopback-устройства; пусто -> автодетект по известным именам."""
    return os.getenv("MTRANSCRIBE_SYSTEM_DEVICE") or None


def outputs_dir() -> Path:
    return Path(os.getenv("MTRANSCRIBE_OUTPUTS", "outputs"))
