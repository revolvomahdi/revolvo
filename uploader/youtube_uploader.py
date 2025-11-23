# Automation/uploader/youtube_uploader.py
# Handles the authenticated uploading of videos to YouTube.

import os
import pickle
from pathlib import Path
import time

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# --- Constants ---
UPLOADER_DIR = Path(__file__).parent
CREDENTIALS_FILE = UPLOADER_DIR / "credentials.json"
UPLOADED_LOG_FILE = UPLOADER_DIR / "uploaded_videos.log"
YOUTUBE_API_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_authenticated_service(token_path, log_function):
    """
    Authenticates with the YouTube API and returns a service object.
    Handles token creation, loading, and refreshing.
    """
    creds = None
    token_file = Path(token_path)

    if token_file.exists():
        try:
            with open(token_file, "rb") as token:
                creds = pickle.load(token)
            log_function(f"ℹ️ Loaded token from {token_file.name}")
        except (pickle.UnpicklingError, EOFError) as e:
            log_function(f"⚠️ Could not load token file {token_file.name}: {e}. It will be recreated.")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                log_function("⌛️ Refreshing expired token...")
                creds.refresh(Request())
                log_function("✅ Token refreshed successfully.")
            except Exception as e:
                log_function(f"❌ Token refresh failed: {e}. Starting new authentication flow.")
                creds = None
        
        if not creds:
            if not CREDENTIALS_FILE.exists():
                error_msg = f"FATAL: Credentials file not found at {CREDENTIALS_FILE}. Please download it from Google Cloud Console."
                log_function(error_msg)
                raise FileNotFoundError(error_msg)
            
            log_function("🚀 Starting new user authentication flow...")
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), YOUTUBE_API_SCOPES)
            creds = flow.run_local_server(port=0)
            log_function("✅ Authentication successful.")

        try:
            with open(token_file, "wb") as token:
                pickle.dump(creds, token)
            log_function(f"💾 Saved new token to {token_file.name}")
        except IOError as e:
            log_function(f"❌ Could not save token file: {e}")

    return build("youtube", "v3", credentials=creds)


def do_upload(youtube_service, video_info, log_function, privacy_status="private"):
    """
    Performs the actual video upload API call.
    """
    video_path = video_info["video_path"]
    if not Path(video_path).exists():
        log_function(f"❌ ERROR: Video file not found, skipping upload: {video_path}")
        return None

    # --- BAŞLIK KONTROLÜ (YENİ) ---
    # YouTube sınırı 100 karakterdir. Eğer uzunsa sonundan kesiyoruz.
    title = video_info["title"]
    if len(title) > 100:
        title = title[:100] # 100. karakterden sonrasını uçur
        # Eğer kesilen yer hashtag'in ortasına geldiyse çirkin durmasın diye son boşluğa kadar temizleyelim (İsteğe bağlı estetik ayar)
        if " " in title:
            title = title.rsplit(" ", 1)[0]
            
    log_function(f"  - Title: {title}") # Kesilmiş halini logla
    log_function(f"  - Status: {privacy_status.capitalize()}")

    request_body = {
        "snippet": {
            "title": title, # Kontrolden geçmiş başlığı kullan
            "description": video_info["description"],
            "tags": video_info["tags"],
            "categoryId": "22"  # Category for "People & Blogs"
        },
        "status": {
            "privacyStatus": privacy_status, 
            "selfDeclaredMadeForKids": False
        }
    }

    try:
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        
        response = youtube_service.videos().insert(
            part=",".join(request_body.keys()),
            body=request_body,
            media_body=media
        ).execute()

        video_id = response.get('id')
        log_function(f"✅ [{video_info['lang'].upper()}] Upload successful! Video ID: {video_id}")
        return video_id

    except Exception as e:
        # Hata mesajını daha temiz gösterelim
        error_msg = str(e)
        if "invalidTitle" in error_msg:
             log_function(f"❌ [{video_info['lang'].upper()}] Title too long error despite truncation. API Error: {e}")
        else:
             log_function(f"❌ [{video_info['lang'].upper()}] An API error occurred during upload: {e}")
        return None


def upload_videos(videos_to_upload, channel_configs, log_function, privacy_status="private"):
    """
    Main function to orchestrate the immediate uploading of a list of videos.
    Accepts privacy_status parameter.
    """
    if not videos_to_upload:
        log_function("ℹ️ No videos in the upload queue.")
        return

    uploaded_videos_log = []
    if UPLOADED_LOG_FILE.exists():
        with open(UPLOADED_LOG_FILE, "r", encoding="utf-8") as f:
            uploaded_videos_log = [line.strip() for line in f]

    for video_info in videos_to_upload:
        lang = video_info.get("lang")
        video_path = video_info.get("video_path")

        if not lang or not video_path:
            log_function(f"⚠️ Skipping video with incomplete metadata: {video_info}")
            continue

        if video_path in uploaded_videos_log:
            log_function(f"ℹ️ Skipping already uploaded video: {Path(video_path).name}")
            continue

        config = channel_configs.get(lang)
        if not config:
            log_function(f"⚠️ No channel configuration found for language '{lang}'. Skipping.")
            continue
        
        log_function(f"\n--- Preparing upload for {config['channel_name']} ({lang.upper()}) ---")

        try:
            youtube = get_authenticated_service(config["token_file"], log_function)
            # privacy_status artık burada iletiliyor
            video_id = do_upload(youtube, video_info, log_function, privacy_status)

            if video_id:
                log_uploaded_video(video_path)

        except FileNotFoundError as e:
            log_function(f"CRITICAL ERROR: {e}")
            break
        except Exception as e:
            log_function(f"An unexpected error occurred for language {lang}: {e}")

def force_reauthorize(token_path, log_function):
    """
    Deletes an existing token and forces a new OAuth 2.0 flow.
    Returns True on success, False on failure.
    """
    token_file = Path(token_path)
    if token_file.exists():
        try:
            os.remove(token_file)
            log_function(f"ℹ️ Deleted existing token: {token_file.name}")
        except OSError as e:
            log_function(f"❌ Could not delete token {token_file.name}: {e}")
            return False

    try:
        if not CREDENTIALS_FILE.exists():
            error_msg = f"FATAL: Credentials file not found at {CREDENTIALS_FILE}."
            log_function(error_msg)
            raise FileNotFoundError(error_msg)

        log_function(f"🚀 Starting new user authentication for {token_file.name}...")
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), YOUTUBE_API_SCOPES)
        creds = flow.run_local_server(port=0)
        
        with open(token_file, "wb") as token:
            pickle.dump(creds, token)
        log_function(f"✅ Authentication successful. Saved new token to {token_file.name}")
        return True
    except Exception as e:
        log_function(f"❌ An error occurred during authorization: {e}")
        return False