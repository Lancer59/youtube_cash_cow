# Architecture — YouTube Shorts Cash Cow

## Overview

A fully automated pipeline that generates, assembles, and (optionally) publishes YouTube Shorts in the history niche. Given a niche topic, the system produces a complete short-form video — with voiceover, stock footage, and burned-in captions — on a recurring schedule, with zero human intervention required.

---

## High-Level Pipeline

```
config.json
    │
    ▼
[1] generator.py  ──── Groq LLM ────►  script + title + description + tags + keywords
    │
    ▼
[2] voiceover.py  ──── Kokoro ONNX (local) ────►  output/voiceover.wav
    │
    ▼
[3] media.py      ──── Pexels API ────►  output/clips/*.mp4
    │                  (stock footage)
    │──── MoviePy + FFmpeg ────►  output/final_<timestamp>.mp4
    │
    ▼
[4] subtitles.py  ──── Whisper (local) ────►  word-level timestamps
    │                  MoviePy composite ────►  output/final_<timestamp>_captioned.mp4
    │
    ▼
[5] uploader.py   ──── YouTube Data API v3 ────►  YouTube (scheduled upload)
    (optional, currently commented out in main.py)
```

---

## Module Breakdown

### `main.py` — Orchestrator
The entry point. Runs the full pipeline sequentially and manages the recurring schedule.

- Calls each stage in order, passing outputs between them
- After the first run, uses `schedule` to repeat every N hours (default: 24)
- YouTube upload is implemented but commented out pending API configuration

### `config.py` + `config.json` — Configuration Layer
A singleton loader that reads `config.json` once and caches it. All modules call `config.get()` to retrieve their settings.

Key config sections:

| Section | Controls |
|---|---|
| `groq` | LLM model and temperature |
| `script` | Niche, word count limits, call-to-action text |
| `voiceover` | Kokoro voice, speed, language, model paths |
| `video` | Resolution (1080×1920), FPS, target duration, clips per keyword |
| `subtitles` | Whisper model, font, size, color, stroke, vertical position |
| `scheduler` | Run interval and YouTube publish hour (UTC) |

### `generator.py` — Script Generation
Uses the Groq API (llama-3.3-70b-versatile) to produce:
- A spoken script (150–250 words) with a hook, 5–6 fact points, and a CTA
- YouTube metadata: title, description, tags
- Stock footage search keywords (3 terms)

Includes retry logic (up to 3 attempts) to enforce minimum word count. Parses the LLM's structured text response into a Python dict.

**External dependency:** Groq API (`GROQ_API_KEY`)

### `voiceover.py` — Text-to-Speech
Converts the generated script to a `.wav` file using **Kokoro ONNX**, a fully local TTS engine.

- Loads the ONNX model and voice binaries from `models/`
- Configurable voice (`af_heart`, `am_adam`, etc.), speed, and language
- No cloud API calls — entirely offline

**Local models:** `models/kokoro-v2.0.onnx`, `models/voices-v1.0.bin`

### `media.py` — Stock Footage + Video Assembly
Two responsibilities:

1. **`fetch_clips(keywords)`** — Queries the Pexels API for portrait-orientation video clips. Downloads up to `clips_per_keyword` clips per keyword until `target_duration` seconds of footage is accumulated. Clips are cached locally in `output/clips/`.

2. **`assemble_video(clip_paths, voiceover_path)`** — Processes each clip with MoviePy: resizes to 1080×1920, center-crops, strips audio, concatenates, then lays the voiceover on top. Output is trimmed to match voiceover duration.

**External dependency:** Pexels API (`PEXELS_API_KEY`)

### `subtitles.py` — Captions
Two responsibilities:

1. **`transcribe(voiceover_path)`** — Runs OpenAI Whisper locally on the `.wav` file with `word_timestamps=True` to get per-word start/end times.

2. **`burn_subtitles(video_path, words)`** — Creates a `TextClip` per word positioned at a configurable Y coordinate, composites them onto the video, and renders the captioned output. Can be disabled via `subtitles.enabled` in config.

**Local model:** Whisper `base` (downloaded automatically on first run)

### `uploader.py` — YouTube Upload
Handles OAuth 2.0 authentication and video upload via the YouTube Data API v3.

- On first run, opens a browser for OAuth consent and saves the token to `token.pickle`
- Subsequent runs use the cached/refreshed token
- Supports scheduled publishing: videos can be uploaded as `private` with a future `publishAt` timestamp
- Default publish time: tomorrow at 18:00 UTC

**External dependency:** Google OAuth (`client_secrets.json`, `YOUTUBE_CLIENT_SECRETS`)

### `logger.py` — Logging
Centralized terminal output using `rich`. Provides themed helpers: `banner()`, `step()`, `info()`, `success()`, `warning()`, `error()`, `done()`, and a `spinner()` context manager.

---

## Data Flow

```
config.json ──► All modules (singleton via config.py)
.env        ──► API keys (GROQ_API_KEY, PEXELS_API_KEY, YOUTUBE_CLIENT_SECRETS)

generator.py
  └─► data = { script, title, description, tags, keywords }

voiceover.py(data["script"])
  └─► output/voiceover.wav

media.py(data["keywords"])
  └─► output/clips/<id>.mp4  (multiple)
  └─► output/final_<ts>.mp4

subtitles.py(output/voiceover.wav, output/final_<ts>.mp4)
  └─► output/final_<ts>_captioned.mp4

uploader.py(output/final_<ts>_captioned.mp4, data["title"], ...)
  └─► YouTube (scheduled)
```

---

## External Services & APIs

| Service | Purpose | Auth | Cost |
|---|---|---|---|
| Groq API | LLM script generation | API key | Free tier |
| Pexels API | Stock video footage | API key | Free |
| Kokoro ONNX | Text-to-speech | None (local) | Free |
| OpenAI Whisper | Speech transcription | None (local) | Free |
| YouTube Data API v3 | Video upload | OAuth 2.0 | Free (quota limits) |

---

## File & Directory Structure

```
youtube_cash_cow/
├── main.py              # Pipeline orchestrator + scheduler
├── config.py            # Config singleton loader
├── config.json          # All tunable settings
├── generator.py         # LLM script generation (Groq)
├── voiceover.py         # TTS synthesis (Kokoro ONNX)
├── media.py             # Stock footage fetch + video assembly (MoviePy)
├── subtitles.py         # Transcription + caption burn-in (Whisper)
├── uploader.py          # YouTube upload (Google API)
├── logger.py            # Rich-based terminal logger
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container build (mounts output/ as volume)
├── .env                 # API keys (gitignored)
├── models/
│   ├── kokoro-v2.0.onnx # Kokoro TTS model
│   └── voices-v1.0.bin  # Kokoro voice data
└── output/
    ├── voiceover.wav
    ├── clips/           # Downloaded stock footage
    └── final_*.mp4      # Raw and captioned final videos
```

---

## Scheduler

After the first pipeline run, `main.py` registers a `schedule` job to repeat every `scheduler.run_every_hours` hours (default: 24). The main thread loops with `time.sleep(60)` polling for pending jobs. Each run produces a new timestamped output file.

---

## Docker

The `Dockerfile` packages the app for containerized runs. The `output/` directory is mounted as a volume so generated videos are accessible on the host. Model files must be downloaded locally before building and are copied into the image.

---

## Key Design Decisions

- **All AI is either free-tier cloud or fully local.** Groq and Pexels use free API tiers; Kokoro ONNX and Whisper run entirely offline with no per-call cost.
- **Config-driven, not code-driven.** Every tunable parameter lives in `config.json`. Changing niche, voice, resolution, or schedule requires no code edits.
- **Clip caching.** Downloaded Pexels clips are written to `output/clips/` and reused if the file already exists, avoiding redundant downloads.
- **Upload decoupled from generation.** The uploader is implemented and ready but commented out in `main.py`, making it easy to generate and review videos locally before enabling publishing.
- **Retry logic on LLM output.** The generator retries up to 3 times if the returned script is below the minimum word count, guarding against underfilled LLM responses.
