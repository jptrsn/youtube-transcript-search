from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from backend.config import YOUTUBE_API_KEY
from typing import List, Dict, Optional
import re

class YouTubeClient:
    def __init__(self):
        self.youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

    def extract_channel_id(self, url: str) -> Optional[str]:
        """Extract channel ID from various YouTube URL formats"""
        patterns = [
            r'youtube\.com/channel/([^/?]+)',
            r'youtube\.com/@([^/?]+)',
            r'youtube\.com/c/([^/?]+)',
            r'youtube\.com/user/([^/?]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                handle_or_id = match.group(1)
                # If it starts with UC, it's already a channel ID
                if handle_or_id.startswith('UC'):
                    return handle_or_id
                # Otherwise, we need to resolve the handle/username
                return self._resolve_channel_id(handle_or_id, url)

        return None

    def _resolve_channel_id(self, handle: str, original_url: str) -> Optional[str]:
        """Resolve a channel handle or username to a channel ID"""
        try:
            # Try as a handle (new @username format)
            if '@' in original_url:
                request = self.youtube.search().list(
                    part='snippet',
                    q=handle,
                    type='channel',
                    maxResults=1
                )
                response = request.execute()
                if response['items']:
                    return response['items'][0]['snippet']['channelId']

            # Try as username (legacy format)
            request = self.youtube.channels().list(
                part='id',
                forUsername=handle
            )
            response = request.execute()
            if response['items']:
                return response['items'][0]['id']

        except HttpError as e:
            print(f"Error resolving channel: {e}")

        return None

    def get_channel_info(self, channel_id: str) -> Optional[Dict]:
        """Get channel metadata"""
        try:
            request = self.youtube.channels().list(
                part='snippet,contentDetails',
                id=channel_id
            )
            response = request.execute()

            if not response['items']:
                return None

            channel = response['items'][0]
            return {
                'channel_id': channel_id,
                'channel_name': channel['snippet']['title'],
                'description': channel['snippet'].get('description', ''),
                'uploads_playlist_id': channel['contentDetails']['relatedPlaylists']['uploads']
            }
        except HttpError as e:
            print(f"Error fetching channel info: {e}")
            return None

    def get_all_videos(self, uploads_playlist_id: str) -> List[Dict]:
        """Get all videos from a channel's uploads playlist (reverse chronological)"""
        videos = []
        next_page_token = None

        try:
            while True:
                request = self.youtube.playlistItems().list(
                    part='snippet,contentDetails',
                    playlistId=uploads_playlist_id,
                    maxResults=50,
                    pageToken=next_page_token
                )
                response = request.execute()

                for item in response['items']:
                    video_data = {
                        'video_id': item['contentDetails']['videoId'],
                        'title': item['snippet']['title'],
                        'description': item['snippet'].get('description', ''),
                        'published_at': item['snippet']['publishedAt'],
                        'thumbnail_url': item['snippet']['thumbnails']['high']['url']
                    }
                    videos.append(video_data)

                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break

                print(f"Fetched {len(videos)} videos so far...")

        except HttpError as e:
            print(f"Error fetching videos: {e}")

        return videos

    def resolve_handle(self, handle: str) -> Optional[str]:
        """Resolve a YouTube handle (@username) to channel ID"""
        try:
            # Remove @ if present
            clean_handle = handle.lstrip('@')

            # Try as username first (legacy /user/ URLs)
            request = self.youtube.channels().list(
                part='id',
                forUsername=clean_handle
            )
            response = request.execute()

            if response.get('items'):
                return response['items'][0]['id']

            # If that didn't work, search for the handle
            request = self.youtube.search().list(
                part='snippet',
                q=clean_handle,
                type='channel',
                maxResults=1
            )
            response = request.execute()

            if response.get('items'):
                return response['items'][0]['snippet']['channelId']

            return None

        except HttpError as e:
            print(f"Error resolving handle {handle}: {e}")
            return None

    def get_video_details(self, video_id: str) -> Optional[Dict]:
        """Get detailed information about a specific video"""
        try:
            request = self.youtube.videos().list(
                part='snippet',
                id=video_id
            )
            response = request.execute()

            if not response['items']:
                return None

            video = response['items'][0]
            snippet = video['snippet']

            return {
                'video_id': video_id,
                'title': snippet['title'],
                'description': snippet.get('description', ''),
                'published_at': snippet['publishedAt'],
                'thumbnail_url': snippet['thumbnails']['high']['url']
            }
        except HttpError as e:
            print(f"Error fetching video details: {e}")
            return None