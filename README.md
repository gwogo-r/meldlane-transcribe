# meldlane-transcribe

Meeting transcription that runs anywhere: turn an audio/video file **or a live mic + system-audio capture** into a structured JSON transcript with a timeline and speakers. Built on [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2) — fast on CPU, no torch, no external ffmpeg for audio formats.

Part of the [Meldlane](https://github.com/) toolchain (project management for AI-first teams), useful standalone.

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

# check your audio setup
mtranscribe doctor
```

Result: `outputs/<timestamp>/transcript.json`

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

For single-track files, full diarization (`spk_0`, `spk_1`, ...) is available as an optional extra: `pip install meldlane-transcribe[diarize]` (pyannote, requires torch + HF token).

## System audio capture

Cascade of strategies, first available wins:

| OS | How | Setup |
|----|-----|-------|
| Windows | **WASAPI loopback** (via `pyaudiowpatch`) | none — works out of the box with any output device (speakers, headphones, Bluetooth) |
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

## License

MIT
