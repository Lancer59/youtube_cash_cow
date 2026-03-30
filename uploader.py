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
from googleapiclient.http import MediaFileUpload
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = "token.pickle"
CLIENT_SECRETS = os.getenv("YOUTUBE_CLIENT_SECRETS", "client_secrets.json")


def get_youtube_client():
    creds = None

    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return build("youtube", "v3", credentials=creds)


def upload_video(video_path: str, title: str, description: str, tags: list, publish_at: datetime = None):
    """
    Upload video to YouTube.
    If publish_at is provided, the video is scheduled (private until that time).
    """
    youtube = get_youtube_client()

    status = "private" if publish_at else "public"
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "27"  # Education
        },
        "status": {
            "privacyStatus": status,
            "selfDeclaredMadeForKids": False
        }
    }

    if publish_at:
        body["status"]["publishAt"] = publish_at.strftime("%Y-%m-%dT%H:%M:%S.000Z")

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")

    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()

    video_id = response.get("id")
    print(f"Uploaded! https://youtube.com/shorts/{video_id}")
    return video_id


def next_publish_time(hour: int = 18):
    """Returns tomorrow at the given UTC hour."""
    now = datetime.now(timezone.utc)
    publish = (now + timedelta(days=1)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return publish


if __name__ == "__main__":
    publish_time = next_publish_time(hour=18)  # Schedule for tomorrow 6PM UTC
    upload_video(
        video_path="output/final.mp4",
        title="Test History Short",
        description="A test upload. #Shorts #History",
        tags=["history", "shorts", "facts"],
        publish_at=publish_time
    )
