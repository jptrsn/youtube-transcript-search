#!/usr/bin/env python3
import sys
import argparse
from datetime import datetime
from sqlalchemy.orm import Session
from backend.database import SessionLocal, init_db
from backend.models import Channel, Video, Transcript, TranscriptError
from backend.youtube_client import YouTubeClient
from backend.transcript_fetcher import TranscriptFetcher

def add_or_update_channel(channel_url: str):
    """Add a new channel or update an existing one"""

    # Initialize database tables if they don't exist
    init_db()

    # Initialize clients
    yt_client = YouTubeClient()
    transcript_fetcher = TranscriptFetcher()
    db: Session = SessionLocal()

    try:
        print(f"🔍 Extracting channel ID from URL: {channel_url}")
        channel_id = yt_client.extract_channel_id(channel_url)

        if not channel_id:
            print("❌ Could not extract channel ID from URL")
            return

        print(f"✅ Channel ID: {channel_id}")

        # Get channel info
        print("📡 Fetching channel information...")
        channel_info = yt_client.get_channel_info(channel_id)

        if not channel_info:
            print("❌ Could not fetch channel information")
            return

        print(f"✅ Channel: {channel_info['channel_name']}")

        # Check if channel exists in database
        existing_channel = db.query(Channel).filter(
            Channel.channel_id == channel_id
        ).first()

        if existing_channel:
            print(f"📝 Updating existing channel: {existing_channel.channel_name}")
            existing_channel.channel_name = channel_info['channel_name']
            existing_channel.description = channel_info['description']
            existing_channel.last_checked = datetime.utcnow()
            existing_channel.updated_at = datetime.utcnow()
            db_channel = existing_channel
        else:
            print(f"➕ Adding new channel: {channel_info['channel_name']}")
            db_channel = Channel(
                channel_id=channel_id,
                channel_name=channel_info['channel_name'],
                channel_url=channel_url,
                description=channel_info['description'],
                last_checked=datetime.utcnow()
            )
            db.add(db_channel)

        db.commit()
        db.refresh(db_channel)

        # Fetch all videos
        print("📹 Fetching all videos from channel...")
        videos = yt_client.get_all_videos(channel_info['uploads_playlist_id'])
        print(f"✅ Found {len(videos)} videos")

        # Process each video
        new_videos = 0
        updated_videos = 0
        new_transcripts = 0

        for idx, video_data in enumerate(videos, 1):
            video_id = video_data['video_id']
            print(f"\n[{idx}/{len(videos)}] Processing: {video_data['title'][:60]}...")

            # Check if video exists
            existing_video = db.query(Video).filter(
                Video.video_id == video_id
            ).first()

            if existing_video:
                print(f"  ✓ Video already in database")
                updated_videos += 1
                db_video = existing_video
            else:
                print(f"  ➕ Adding new video")
                db_video = Video(
                    channel_id=db_channel.id,
                    video_id=video_id,
                    title=video_data['title'],
                    description=video_data['description'],
                    published_at=datetime.fromisoformat(video_data['published_at'].replace('Z', '+00:00')),
                    thumbnail_url=video_data['thumbnail_url']
                )
                db.add(db_video)
                db.commit()
                db.refresh(db_video)
                new_videos += 1

            # Check if transcript exists
            existing_transcript = db.query(Transcript).filter(
                Transcript.video_id == db_video.id
            ).first()

            if existing_transcript:
                print(f"  ✓ Transcript already exists")
                continue

            # Fetch transcript
            print(f"  📝 Fetching transcript...")
            transcript_data, error_data = transcript_fetcher.fetch_transcript(video_id)

            if transcript_data:
                db_transcript = Transcript(
                    video_id=db_video.id,
                    text=transcript_data['text'],
                    snippets=transcript_data['snippets'],
                    language_code=transcript_data['language_code'],
                    is_generated=transcript_data['is_generated']
                )
                db.add(db_transcript)
                db.commit()
                new_transcripts += 1
                print(f"  ✅ Transcript saved ({len(transcript_data['text'])} characters)")
            elif error_data:
                # Log the error to database
                db_error = TranscriptError(
                    video_id=db_video.id,
                    error_type=error_data['error_type'],
                    error_message=error_data['error_message']
                )
                db.add(db_error)
                db.commit()

        # Update channel last_checked timestamp
        db_channel.last_checked = datetime.utcnow()
        db.commit()

        print("\n" + "="*60)
        print("✅ COMPLETE!")
        print(f"📊 Summary:")
        print(f"   - Channel: {channel_info['channel_name']}")
        print(f"   - Total videos: {len(videos)}")
        print(f"   - New videos added: {new_videos}")
        print(f"   - Videos updated: {updated_videos}")
        print(f"   - New transcripts fetched: {new_transcripts}")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(
        description='Add or update a YouTube channel and fetch all video transcripts'
    )
    parser.add_argument(
        'channel_url',
        help='YouTube channel URL (e.g., https://youtube.com/@channelname)'
    )

    args = parser.parse_args()
    add_or_update_channel(args.channel_url)

if __name__ == "__main__":
    main()