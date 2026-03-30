FROM python:3.11-slim

# Install ffmpeg (required by Whisper) and fonts
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and config
COPY *.py ./
COPY config.json ./

# Kokoro model files (must be present in models/ before building)
COPY models/kokoro-v1.0.onnx ./models/
COPY models/voices-v1.0.bin ./models/

# Output folder
RUN mkdir -p output/clips

# Env vars are passed at runtime via --env-file or -e flags
CMD ["python", "main.py"]
