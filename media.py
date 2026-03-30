"""
media.py
Downloads stock footage from Pexels and assembles the final video using MoviePy.
"""

import os
import requests
from datetime import datetime
from dotenv import load_dotenv
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips
import logger
from config import get

load_dotenv()
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")


def fetch_clips(keywords: list):
    cfg = get()["video"]
    total_duration = cfg["target_duration"]
    per_page = cfg["clips_per_keyword"]

    os.makedirs("output/clips", exist_ok=True)
    downloaded = []

    for keyword in keywords:
        if sum(c[1] for c in downloaded) >= total_duration:
            break

        url = "https://api.pexels.com/videos/search"
        headers = {"Authorization": PEXELS_API_KEY}
        params = {"query": keyword, "per_page": per_page, "orientation": "portrait"}

        res = requests.get(url, headers=headers, params=params)
        videos = res.json().get("videos", [])

        for video in videos:
            if sum(c[1] for c in downloaded) >= total_duration:
                break

            duration = video.get("duration", 0)
            if duration < 3:
                continue

            files = sorted(video["video_files"], key=lambda x: x.get("width", 0), reverse=True)
            video_url = files[0]["link"]

            logger.info(f"Downloading clip {video['id']} ({duration}s)...")
            path = f"output/clips/{video['id']}.mp4"
            if not os.path.exists(path):
                r = requests.get(video_url, stream=True)
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            downloaded.append((path, duration))

    return [c[0] for c in downloaded]


def assemble_video(clip_paths: list, voiceover_path: str, output_path: str = None):
    cfg = get()["video"]
    VIDEO_W = cfg["width"]
    VIDEO_H = cfg["height"]
    FPS = cfg["fps"]

    os.makedirs("output", exist_ok=True)
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"output/final_{timestamp}.mp4"

    clips = []
    for path in clip_paths:
        clip = VideoFileClip(path).without_audio()
        clip = clip.resized(height=VIDEO_H)
        if clip.w < VIDEO_W:
            clip = clip.resized(width=VIDEO_W)
        clip = clip.cropped(x_center=clip.w / 2, y_center=clip.h / 2, width=VIDEO_W, height=VIDEO_H)
        clips.append(clip)

    audio = AudioFileClip(voiceover_path)
    total_duration = audio.duration

    video = concatenate_videoclips(clips, method="compose")
    video = video.subclipped(0, min(total_duration, video.duration))
    video = video.with_audio(audio)

    video.write_videofile(output_path, fps=FPS, codec="libx264", audio_codec="aac", logger=None)
    logger.success(f"Video saved → {output_path}")
    return output_path


if __name__ == "__main__":
    paths = fetch_clips(["ancient rome", "history", "war"])
    assemble_video(paths, "output/voiceover.wav")
