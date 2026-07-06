# meldlane-transcribe

[Русская версия](README.ru.md)

![Python](https://img.shields.io/badge/python-3.11%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green) ![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)

Meeting transcription that runs anywhere: turn an audio/video file **or a live mic + system-audio capture** into a structured JSON transcript with a timeline and speakers. Built on [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) — fast on CPU, no torch, no external ffmpeg for audio formats.

Standalone tool; also the first building block of the Meldlane toolchain (project management for AI-first teams).

## Why

- **Zero-setup**: `pip install`, run, done — no ffmpeg, no GPU, no cloud API keys.
- **Speakers for free**: live capture records mic and system audio as separate tracks, so "me" vs "others" attribution needs no ML model at all.
- **Works on Windows without extra drivers**: WASAPI loopback captures system audio from any output device (speakers, headphones, Bluetooth) out of the box.
- **Structured output**: one JSON contract (`meeting_id`, `segments[{start, end, speaker, text}]`) plus a plain `.txt` for humans.

## Install

```bash
pip install meldlane-transcribe        # or: uvx meldlane-transcribe --help
```

Python 3.11+. Windows and macOS.

## Usage

```bash
# transcribe a file (mp3, wav, m4a, ogg, aac, flac + mp4/mkv/webm/... video)
mtranscribe file meeting.mp3

# record live (mic + system audio if a loopback device is found), stop from another terminal
mtranscribe record
mtranscribe stop

# or record a fixed duration
mtranscribe record --seconds 300

# check your audio setup: which devices, which capture strategy will be used
mtranscribe doctor
```

Result: `outputs/<timestamp>/transcript.json` (+ `transcript.txt` alongside it — plain `[mm:ss speaker] text` lines for reading).

```json
{
  "meeting_id": "a1b2c3",
  "lang": "ru",
  "duration_sec": 3612.4,
  "source": {"type": "live", "path": null},
  "created_at": "2026-07-02T18:00:00Z",
  "segments": [
    {"start": 0.0, "end": 4.2, "speaker": "me", "text": "..."}
  ]
}
```

## Speakers without ML

During live capture the mic and system audio are recorded as **separate tracks**, so speaker attribution is free: everything from your mic is `me`, everything from the loopback is `others`. No diarization model, no GPU, no tokens.

**Limitation:** this only tells apart "me" vs "everyone else" — if multiple people are talking on the other side of the call, they all land in `others` undivided, since a channel has no notion of individual voices. Telling *them* apart from each other requires voice-based diarization.

For single-track files, or to split `others` into individual speakers, full diarization (`spk_0`, `spk_1`, ...) is available as an optional extra: `pip install meldlane-transcribe[diarize]` (pyannote, requires torch + a free HuggingFace token) — deliberately not in core, to keep the zero-setup install promise.

## System audio capture

Cascade of strategies, first available wins:

| OS | How | Setup |
|----|-----|-------|
| Windows | **WASAPI loopback** (via `pyaudiowpatch`) | none — works out of the box with any output device |
| Windows (fallback) | Stereo Mix / VB-Cable (auto-detected) | enable Stereo Mix in Sound settings, or install VB-Cable |
| macOS | BlackHole (auto-detected) | `brew install blackhole-2ch` |

No loopback available? `mtranscribe record` still works with mic only, and `mtranscribe doctor` tells you exactly what to do and which strategy is active.

## Configuration (env vars, all optional)

| Var | Default | Meaning |
|-----|---------|---------|
| `MTRANSCRIBE_MODEL` | `base` | Whisper model: tiny/base/small/medium/large |
| `MTRANSCRIBE_LANGUAGE` | auto | force language, e.g. `ru` |
| `MTRANSCRIBE_MIC_DEVICE` | system default | mic device name substring |
| `MTRANSCRIBE_SYSTEM_DEVICE` | auto-detect | loopback device name substring |
| `MTRANSCRIBE_OUTPUTS` | `./outputs` | where sessions are stored |

Audio tracks are deleted after transcription unless you pass `--keep-audio`.

## Roadmap

- [ ] `pyannote` extra for splitting `others` into individual speakers
- [ ] Verified macOS/BlackHole support
- [ ] Video container testing (mp4/mkv/webm) beyond audio-only files

## License

MIT
