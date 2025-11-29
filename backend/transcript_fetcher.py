from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
    RequestBlocked,
    IpBlocked,
    YouTubeRequestFailed,
    AgeRestricted
)
from typing import Optional, Dict, Tuple
import time

class IpBlockedException(Exception):
    """Raised when IP is blocked - should stop all transcript fetching"""
    pass

class TranscriptFetcher:
    def __init__(self):
        self.api = YouTubeTranscriptApi()

    def fetch_transcript(self, video_id: str, max_retries: int = 3) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Fetch English transcript for a video with exponential backoff on rate limits.

        Returns:
            Tuple of (transcript_data, error_data)
            - transcript_data: Dict with 'text', 'snippets', 'language_code', 'is_generated' or None
            - error_data: Dict with 'error_type' and 'error_message' or None

        Raises:
            IpBlockedException: When IP is blocked - caller should stop all processing
        """
        retry_delay = 10  # Start with 10 seconds

        for attempt in range(max_retries):
            try:
                transcript = self.api.fetch(video_id)
                raw_data = transcript.to_raw_data()

                # Combine all text segments into one string for full-text search
                full_text = ' '.join([segment['text'] for segment in raw_data])

                return {
                    'text': full_text,
                    'snippets': raw_data,
                    'language_code': transcript.language_code,
                    'is_generated': transcript.is_generated
                }, None

            except (RequestBlocked) as e:
                # IP is blocked - raise exception to stop all processing
                print(f"  ❌ Request blocked for video {video_id} - stopping all transcript fetching")
                raise IpBlockedException(f"IP is blocked: {str(e)}")

            except (IpBlocked) as e:
                # IP is blocked - raise exception to stop all processing
                print(f"  ❌ IP blocked for video {video_id} - stopping all transcript fetching")
                raise IpBlockedException(f"IP is blocked: {str(e)}")

            except (YouTubeRequestFailed) as e:
                # These might be temporary - retry with backoff
                if attempt < max_retries - 1:
                    print(f"  ⏸️  Request blocked/rate limited ({type(e).__name__}). Waiting {retry_delay} seconds before retry {attempt + 1}/{max_retries}...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    error_type = type(e).__name__
                    error_message = str(e)
                    print(f"  ❌ Request failed after {max_retries} retries: {error_type}")
                    return None, {'error_type': error_type, 'error_message': error_message}

            except AgeRestricted as e:
                print(f"  ⚠️  Video {video_id} is age-restricted")
                return None, {'error_type': 'AgeRestricted', 'error_message': str(e)}
            except TranscriptsDisabled as e:
                print(f"  ⚠️  Transcripts disabled for video {video_id}")
                return None, {'error_type': 'TranscriptsDisabled', 'error_message': str(e)}
            except NoTranscriptFound as e:
                print(f"  ⚠️  No English transcript found for video {video_id}")
                return None, {'error_type': 'NoTranscriptFound', 'error_message': str(e)}
            except VideoUnavailable as e:
                print(f"  ⚠️  Video {video_id} is unavailable")
                return None, {'error_type': 'VideoUnavailable', 'error_message': str(e)}
            except Exception as e:
                error_type = type(e).__name__
                error_message = str(e)
                print(f"  ⚠️  Unexpected error: {error_type} - {error_message}")
                return None, {'error_type': error_type, 'error_message': error_message}

        return None, None