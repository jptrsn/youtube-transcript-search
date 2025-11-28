#!/usr/bin/env python3
import sys
import argparse
from backend.database import SessionLocal, init_db
from backend.services.channel_service import ChannelService

def progress_callback(event: str, data: dict):
    """Print progress updates to console"""
    if event == 'status':
        print(f"🔍 {data['message']}")
    elif event == 'channel_id_extracted':
        print(f"✅ Channel ID: {data['channel_id']}")
    elif event == 'channel_info':
        print(f"✅ Channel: {data['channel_name']}")
    elif event == 'videos_found':
        print(f"📹 Found {data['count']} videos")
    elif event == 'video_progress':
        title = data['title'][:60]
        print(f"[{data['current']}/{data['total']}] Processing: {title}...")
    elif event == 'video_status':
        status = data['status']
        if status == 'has_transcript':
            print(f"  ✓ Transcript already exists")
        elif status == 'fetching_transcript':
            print(f"  📝 Fetching transcript...")
        elif status == 'transcript_saved':
            print(f"  ✅ Transcript saved ({data.get('length', 0)} characters)")
        elif status == 'error':
            print(f"  ⚠️  Error: {data['error_type']}")
    elif event == 'complete':
        print("\n" + "="*60)
        print("✅ COMPLETE!")
        print(f"📊 Summary:")
        print(f"   - Channel: {data['channel_name']}")
        print(f"   - Total videos: {data['total_videos']}")
        print(f"   - New videos added: {data['new_videos']}")
        print(f"   - Videos updated: {data['updated_videos']}")
        print(f"   - New transcripts fetched: {data['new_transcripts']}")
        print("="*60)
    elif event == 'error':
        print(f"\n❌ Error: {data['message']}")

def main():
    parser = argparse.ArgumentParser(
        description='Add or update a YouTube channel and fetch all video transcripts'
    )
    parser.add_argument(
        'channel_url',
        help='YouTube channel URL (e.g., https://youtube.com/@channelname)'
    )

    args = parser.parse_args()

    # Initialize database
    init_db()

    # Create service and run
    db = SessionLocal()
    try:
        service = ChannelService(db, progress_callback=progress_callback)
        service.add_or_update_channel(args.channel_url)
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()