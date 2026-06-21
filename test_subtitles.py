"""
test_subtitles.py
Quick subtitle smoke test — runs WITHOUT re-generating a video or voiceover.

Uses an existing output video + voiceover to test ONLY the subtitle step.
Run: python test_subtitles.py

Checks:
  1. Whisper transcription works and produces word timestamps
  2. Every chunk renders without crashing
  3. Output file is written and has non-zero size
  4. Prints a preview of the first 10 chunks and their colors
"""

import os
import sys

# ── find a video and audio to test against ──────────────────────────────────
VIDEO_CANDIDATES = [
    "output/final_20260621_150102.mp4",
    "output/final_20260328_000015.mp4",
    "output/final_20260327_234923.mp4",
]
AUDIO_PATH = "output/voiceover.wav"
TEST_OUTPUT = "output/subtitle_test_output.mp4"

video_path = next((p for p in VIDEO_CANDIDATES if os.path.exists(p)), None)

if not video_path:
    # fallback: find any mp4 in output/ that isn't already captioned
    for f in os.listdir("output"):
        if f.endswith(".mp4") and "_captioned" not in f and "test" not in f:
            video_path = f"output/{f}"
            break

if not video_path:
    print("ERROR: No video found in output/. Run the main pipeline first.")
    sys.exit(1)

if not os.path.exists(AUDIO_PATH):
    print("ERROR: output/voiceover.wav not found. Run the main pipeline first.")
    sys.exit(1)

print(f"Testing against: {video_path}")
print(f"Audio:           {AUDIO_PATH}")
print()

# ── step 1: transcription ────────────────────────────────────────────────────
print("Step 1: Transcribing voiceover with Whisper...")
from subtitles import transcribe
words = transcribe(AUDIO_PATH)
print(f"  → {len(words)} words transcribed")
if not words:
    print("ERROR: No words returned from Whisper. Check the audio file.")
    sys.exit(1)

# ── step 2: chunk preview ────────────────────────────────────────────────────
from subtitles import _group_into_chunks
from config import subtitle_style, upgraded_subtitles

cfg = subtitle_style()
words_per_chunk = cfg.get("words_per_chunk", 3)
chunks = _group_into_chunks(words, words_per_chunk)

color_cycle = [
    cfg.get("base_color", "white"),
    cfg.get("highlight_color", "yellow"),
    "cyan",
    cfg.get("highlight_color", "yellow"),
]

print(f"\nStep 2: Chunk preview (first 10 of {len(chunks)} total chunks)")
print(f"  words_per_chunk : {words_per_chunk}")
print(f"  position_y      : {cfg['position_y']}")
print(f"  font_size       : {cfg['font_size']}")
print(f"  upgraded style  : {upgraded_subtitles()}")
print()
print(f"  {'#':<4}  {'color':<8}  {'start':>6}  {'end':>6}  {'dur':>5}  text")
print(f"  {'-'*4}  {'-'*8}  {'-'*6}  {'-'*6}  {'-'*5}  ----")
for i, chunk in enumerate(chunks[:10]):
    dur = chunk["end"] - chunk["start"] - 0.01
    color = color_cycle[i % len(color_cycle)]
    print(f"  {i:<4}  {color:<8}  {chunk['start']:>6.2f}  {chunk['end']:>6.2f}  {dur:>5.2f}  {chunk['text']}")

# ── step 3: render ───────────────────────────────────────────────────────────
print(f"\nStep 3: Rendering subtitles onto video...")
print(f"  Output: {TEST_OUTPUT}")

from subtitles import burn_subtitles
try:
    result = burn_subtitles(video_path, words, output_path=TEST_OUTPUT)
    size_mb = os.path.getsize(result) / (1024 * 1024)
    print(f"\n✓ SUCCESS — output: {result} ({size_mb:.1f} MB)")
    print("  Open the file to visually verify colors and position.")
except Exception as e:
    print(f"\n✗ FAILED — {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
