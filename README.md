# YouTube Shorts Cash Cow — History Niche

Fully automated. 100% free. Generates and saves history shorts daily.

## Stack
- **Script**: Groq (llama-3.3-70b-versatile)
- **Voiceover**: Kokoro ONNX (local, free)
- **Footage**: Pexels API (free)
- **Subtitles**: OpenAI Whisper (local, free)
- **Assembly**: MoviePy + FFmpeg

---

## Local Setup

### 1. Clone and install
```bash
git clone <your-repo>
cd youtube-cash-cow
pip install -r requirements.txt
```

### 2. Get free API keys
- **Groq**: https://console.groq.com → Create API Key
- **Pexels**: https://www.pexels.com/api → Get Free API Key

### 3. Create your .env
```
GROQ_API_KEY=your_key_here
PEXELS_API_KEY=your_key_here
```

### 4. Download Kokoro model files
```bash
mkdir models
curl -L -o models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v1.0.onnx
curl -L -o models/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices-v1.0.bin
```

### 5. Run
```bash
python main.py
```

---

## Docker

### Build
```bash
mkdir models
curl -L -o models/kokoro-v1.0.onnx https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/kokoro-v1.0.onnx
curl -L -o models/voices-v1.0.bin https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files/voices-v1.0.bin

docker build -t shorts-cash-cow .
```

### Run
```bash
docker run --env-file .env -v $(pwd)/output:/app/output shorts-cash-cow
```

On Windows (CMD):
```cmd
docker run --env-file .env -v %cd%/output:/app/output shorts-cash-cow
```

Videos are saved to the `output/` folder on your host machine.

---

## Configuration

All settings are in `config.json` — no need to touch the code.

| Key | Description |
|---|---|
| `groq.model` | Groq LLM model |
| `groq.temperature` | Creativity (higher = more varied) |
| `script.max_words` | Script length |
| `script.topics` | Historical topics to rotate through |
| `script.excluded_topics` | Topics to never pick |
| `voiceover.voice` | Kokoro voice (e.g. `af_heart`, `am_adam`) |
| `voiceover.speed` | Speech speed (1.2 = 20% faster) |
| `video.width/height` | Resolution (default 1080x1920 vertical) |
| `video.fps` | Frame rate |
| `subtitles.enabled` | Toggle captions on/off |
| `subtitles.font_size` | Caption size |
| `scheduler.run_every_hours` | How often to generate a new video |

---

## Notes
- `.env`, `token.pickle`, `client_secrets.json`, and model files are gitignored — never committed
- `output/` folder is gitignored — videos stay local
- YouTube upload is implemented in `uploader.py` but commented out in `main.py` until you configure the API
