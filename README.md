# YouTube Shorts Cash Cow

Fully automated. 100% free. Three switchable pipelines, one config toggle.

## Pipelines

| Mode | Type | Background | Script Source |
|------|------|------------|---------------|
| **0** | Stock Footage (original) | Pexels API clips | Groq — history narration |
| **1** | Reddit Story | Gameplay loop | r/TIFU / r/AmItheAsshole scrape |
| **2** | Did You Know | Gameplay loop | Groq — shocking facts |

**Mode 3** is not a separate pipeline — it's an **upgraded subtitle style** (chunked text + yellow highlight) that applies on top of any mode above.

---

## Switching Mode

Open `config.json` and change **one value**:

```json
"mode": {
  "active": 0,
  "upgraded_subtitles": true
}
```

- `active`: `0`, `1`, or `2`
- `upgraded_subtitles`: `true` = chunked captions with yellow highlight / `false` = original word-by-word white text

---

## Stack

- **Script**: Groq (`llama-3.3-70b-versatile`) — free
- **Reddit scrape**: PRAW — free (read-only, no OAuth)
- **Voiceover**: Kokoro ONNX (local) — free
- **Stock footage**: Pexels API — free (Mode 0 only)
- **Gameplay background**: local file you provide — free
- **Subtitles**: OpenAI Whisper (local) — free
- **Assembly**: MoviePy + FFmpeg

---

## Setup

### 1. Clone and install

```bash
git clone <your-repo>
cd youtube-cash-cow
pip install -r requirements.txt
```

### 2. Create `.env`

Copy `.env.example` → `.env` and fill in keys:

```
GROQ_API_KEY=...          # all modes — https://console.groq.com
PEXELS_API_KEY=...        # mode 0 only — https://www.pexels.com/api/
REDDIT_CLIENT_ID=...      # mode 1 only
REDDIT_CLIENT_SECRET=...  # mode 1 only
```

**Reddit keys (Mode 1):**
1. Go to https://www.reddit.com/prefs/apps
2. "Create another app" → choose **script**
3. Redirect URI: `http://localhost:8080`
4. Copy the client ID (below app name) and secret

### 3. Download Kokoro model files

```bash
mkdir models
curl -L -o models/kokoro-v2.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v2/kokoro-v2.0.onnx
curl -L -o models/voices-v1.0.bin   https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices-v1.0.bin
```

### 4. Add gameplay video (Modes 1 & 2)

Download any free vertical gameplay clip and save it as `assets/gameplay.mp4`.

Free sources:
- https://pixabay.com/videos/search/minecraft/
- https://pixabay.com/videos/search/subway%20surfers/

See `assets/README.txt` for tips.

### 5. Run

```bash
python main.py
```

---

## Configuration Reference

All settings in `config.json`. Key ones:

| Key | Description |
|-----|-------------|
| `mode.active` | **0**, **1**, or **2** — switches the whole pipeline |
| `mode.upgraded_subtitles` | `true` = chunked yellow-highlight captions (Mode 3 style) |
| `mode0_stock_footage.script.niche` | Topic for history narration (e.g. `"history"`, `"science"`) |
| `mode1_reddit_story.subreddits` | List of subreddits to pull stories from |
| `mode1_reddit_story.min_score` | Minimum upvotes — filters out weak posts |
| `mode2_did_you_know.niche` | Topic for facts (e.g. `"psychology"`, `"finance"`) |
| `mode2_did_you_know.facts_per_video` | How many facts per Short |
| `mode1/2.gameplay_video` | Path to your local gameplay video |
| `voiceover.voice` | Kokoro voice — try `af_heart`, `am_adam`, `bm_george` |
| `subtitles.upgraded.words_per_chunk` | Words per caption chunk (2–3 recommended) |
| `subtitles.upgraded.highlight_color` | Emphasis word color (default: `yellow`) |
| `scheduler.run_every_hours` | Auto-generate interval |

---

## Notes

- `.env`, `token.pickle`, `client_secrets.json`, and model files are gitignored
- `output/` and `assets/gameplay.mp4` are gitignored — stay local
- YouTube upload is in `uploader.py` — uncomment in `main.py` once API is configured
