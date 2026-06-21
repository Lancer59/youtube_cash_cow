"""
uploader.py
Uploads the final video to YouTube using the YouTube Data API v3.
On first run it will open a browser to authenticate - after that it saves a token.
"""

import os
import pickle
from datetime import datetime, timezone, timedelta
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv
import logger

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.pickle"
CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")

# Resumable upload chunk size: 5 MB
CHUNK_SIZE = 5 * 1024 * 1024


def get_youtube_client():
    logger.info("Loading YouTube credentials...")
    creds = None

    if os.path.exists(TOKEN_FILE):
        logger.info(f"Found existing token at '{TOKEN_FILE}'")
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)
    else:
        logger.warning(f"No token file found at '{TOKEN_FILE}' — OAuth flow will open in browser")

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Token expired — refreshing...")
            creds.refresh(Request())
            logger.success("Token refreshed")
        else:
            logger.info(f"Starting OAuth flow using secrets file: '{CLIENT_SECRETS}'")
            if not os.path.exists(CLIENT_SECRETS):
                raise FileNotFoundError(
                    f"Client secrets file not found: '{CLIENT_SECRETS}'. "
                    "Download it from Google Cloud Console → APIs & Services → Credentials."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
            logger.success("OAuth authentication complete")

        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)
        logger.info(f"Token saved → '{TOKEN_FILE}'")
    else:
        logger.success("Credentials valid — no refresh needed")

    return build("youtube", "v3", credentials=creds)


def upload_video(
    video_path: str,
    title: str,
    description: str,
    tags: list,
    publish_at: datetime = None
) -> str | None:
    """
    Upload a video to YouTube with chunked resumable upload and live progress logging.
    Returns the YouTube video ID on success, or None on failure.

    If publish_at is provided, the video is scheduled (set to private until that time).
    """

    # --- Pre-flight checks ---
    if not os.path.exists(video_path):
        logger.error(f"Video file not found: '{video_path}' — aborting upload")
        return None

    file_size_mb = os.path.getsize(video_path) / (1024 * 1024)
    logger.info(f"Video file: '{video_path}' ({file_size_mb:.1f} MB)")
    logger.info(f"Title: {title}")
    logger.info(f"Tags: {', '.join(tags)}")

    if publish_at:
        logger.info(f"Scheduled publish time: {publish_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    else:
        logger.info("Privacy: public (no scheduled time set)")

    # --- Build request body ---
    privacy_status = "private" if publish_at else "public"
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "27"  # Education
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": False
        }
    }

    if publish_at:
        body["status"]["publishAt"] = publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    # --- Authenticate and build request ---
    try:
        youtube = get_youtube_client()
    except FileNotFoundError as e:
        logger.error(str(e))
        return None
    except Exception as e:
        logger.error(f"Failed to authenticate with YouTube: {e}")
        return None

    media = MediaFileUpload(
        video_path,
        chunksize=CHUNK_SIZE,
        resumable=True,
        mimetype="video/mp4"
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    # --- Chunked upload with progress logging ---
    logger.info("Starting chunked resumable upload...")
    logger.info(f"Chunk size: {CHUNK_SIZE // (1024 * 1024)} MB per chunk")

    response = None
    last_logged_pct = -1

    try:
        while response is None:
            status, response = request.next_chunk()

            if status is not None:
                pct = int(status.progress() * 100)
                # Log every 10% to avoid spamming
                if pct >= last_logged_pct + 10:
                    uploaded_mb = file_size_mb * status.progress()
                    logger.info(
                        f"Upload progress: {pct}% "
                        f"({uploaded_mb:.1f} / {file_size_mb:.1f} MB)"
                    )
                    last_logged_pct = pct

    except HttpError as e:
        logger.error(f"YouTube API error during upload: HTTP {e.resp.status} — {e.content.decode()}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        return None

    # --- Validate response ---
    if response is None:
        logger.error("Upload finished but received no response from YouTube API")
        return None

    video_id = response.get("id")
    if not video_id:
        logger.error(f"Upload response missing video ID. Full response: {response}")
        return None

    upload_status = response.get("status", {}).get("uploadStatus", "unknown")
    privacy = response.get("status", {}).get("privacyStatus", "unknown")

    logger.success(f"Upload complete — video ID: {video_id}")
    logger.success(f"Upload status: {upload_status} | Privacy: {privacy}")
    logger.success(f"URL: https://youtube.com/shorts/{video_id}")

    if publish_at:
        logger.info(
            f"Video is PRIVATE and scheduled to go public at "
            f"{publish_at.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
    else:
        logger.success("Video is PUBLIC and live now")

    return video_id


def next_publish_time(hour: int = 18):
    """Returns tomorrow at the given UTC hour."""
    now = datetime.now(timezone.utc)
    publish = (now + timedelta(days=1)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    )
    return publish


if __name__ == "__main__":
    publish_time = next_publish_time(hour=18)
    upload_video(
        video_path="output/final.mp4",
        title="Test History Short",
        description="A test upload. #Shorts #History",
        tags=["history", "shorts", "facts"],
        publish_at=publish_time
    )
