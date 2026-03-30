"""
main.py
Runs the full pipeline: generate script → voiceover → video → subtitles → save.
"""

import schedule
import time
import logger
from config import get
from generator import generate_script
from voiceover import generate_voiceover
from media import fetch_clips, assemble_video
from subtitles import transcribe, burn_subtitles
# from uploader import upload_video, next_publish_time


def run_pipeline():
    logger.banner()
    TOTAL_STEPS = 5

    # Step 1: Generate script
    logger.step(1, TOTAL_STEPS, "Generating history script with Groq...")
    data = generate_script()
    logger.info(f"Title: {data['title']}")
    logger.info(f"Keywords: {', '.join(data['keywords'])}")
    logger.success("Script generated")

    # Step 2: Generate voiceover
    logger.step(2, TOTAL_STEPS, "Converting script to voiceover...")
    voiceover_path = generate_voiceover(data["script"])
    logger.success(f"Voiceover saved → {voiceover_path}")

    # Step 3: Fetch stock footage + assemble video
    logger.step(3, TOTAL_STEPS, "Fetching stock footage from Pexels...")
    clip_paths = fetch_clips(data["keywords"])
    logger.info(f"Downloaded {len(clip_paths)} clip(s)")

    logger.info("Assembling video...")
    video_path = assemble_video(clip_paths, voiceover_path)
    logger.success(f"Raw video assembled → {video_path}")

    # Step 4: Burn subtitles
    logger.step(4, TOTAL_STEPS, "Transcribing voiceover and burning subtitles...")
    words = transcribe(voiceover_path)
    logger.info(f"Transcribed {len(words)} word(s)")
    video_path = burn_subtitles(video_path, words)
    logger.success(f"Captioned video saved → {video_path}")

    # Step 5: Done
    logger.step(5, TOTAL_STEPS, "Finalizing...")
    logger.done(video_path)

    # --- YouTube upload (commented out until API is configured) ---
    # publish_time = next_publish_time(hour=18)
    # upload_video(
    #     video_path=video_path,
    #     title=data["title"],
    #     description=data["description"],
    #     tags=data["tags"],
    #     publish_at=publish_time
    # )


if __name__ == "__main__":
    run_pipeline()

    schedule.every(get()["scheduler"]["run_every_hours"]).hours.do(run_pipeline)

    logger.info("Scheduler running every 24 hours. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)
