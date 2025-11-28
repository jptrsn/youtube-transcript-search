#!/usr/bin/env python3
import argparse
from backend.database import SessionLocal
from backend.models import Channel, Video, Transcript, TranscriptError
from backend.transcript_fetcher import TranscriptFetcher

# Errors that are permanent and should not be retried
PERMANENT_ERRORS = {
    'AgeRestricted',
    'TranscriptsDisabled',
    'NoTranscriptFound',
    'VideoUnavailable'
}

def progress_callback(event: str, data: dict):
    """Print progress updates to console"""
    if event == 'status':
        print(f"🔍 {data['message']}")
    elif event == 'videos_to_retry':
        print(f"📝 Found {data['count']} videos to retry")
    elif event == 'video_progress':
        title = data['title'][:60]
        print(f"[{data['current']}/{data['total']}] {title}...")
    elif event == 'video_status':
        status = data['status']
        if status == 'transcript_saved':
            print(f"  ✅ Transcript saved")
        elif status == 'error':
            print(f"  ❌ Failed: {data['error_type']}")
    elif event == 'complete':
        print("\n" + "="*60)
        print("✅ RETRY COMPLETE!")
        print(f"📊 Summary:")
        print(f"   - Channel: {data['channel_name']}")
        print(f"   - Videos processed: {data['videos_processed']}")
        print(f"   - Successfully fetched: {data['new_transcripts']}")
        print("="*60)

def retry_missing_transcripts(
    channel_url: str = None,
    retry_all: bool = False,
    retry_errors: str = None
):
    """
    Retry fetching transcripts for videos that don't have them

    Args:
        channel_url: Optional channel URL to filter by
        retry_all: If True, retry all videos without transcripts including those with permanent errors
        retry_errors: Comma-separated list of specific error types to retry
    """

    db = SessionLocal()
    transcript_fetcher = TranscriptFetcher()

    try:
        # Build query for videos without transcripts
        query = db.query(Video).outerjoin(Transcript).filter(Transcript.id == None)

        # If channel URL provided, filter by channel
        if channel_url:
            channel = db.query(Channel).filter(Channel.channel_url == channel_url).first()
            if not channel:
                print(f"❌ Channel not found: {channel_url}")
                return
            query = query.filter(Video.channel_id == channel.id)
            print(f"🔍 Finding videos without transcripts for channel: {channel.channel_name}")
        else:
            print("🔍 Finding all videos without transcripts across all channels")

        # Handle error filtering
        if not retry_all:
            if retry_errors:
                # Retry only specific error types
                error_types = [e.strip() for e in retry_errors.split(',')]
                print(f"🎯 Only retrying videos with errors: {', '.join(error_types)}")

                videos_with_errors = db.query(TranscriptError.video_id).filter(
                    TranscriptError.error_type.in_(error_types)
                ).distinct()
                query = query.filter(Video.id.in_(videos_with_errors))
            else:
                # Default: exclude videos with permanent errors
                print(f"⏭️  Skipping videos with permanent errors: {', '.join(PERMANENT_ERRORS)}")

                videos_with_permanent_errors = db.query(TranscriptError.video_id).filter(
                    TranscriptError.error_type.in_(PERMANENT_ERRORS)
                ).distinct()
                query = query.filter(~Video.id.in_(videos_with_permanent_errors))
        else:
            print("🔄 Retrying ALL videos without transcripts (including permanent errors)")

        videos_without_transcripts = query.all()

        if not videos_without_transcripts:
            print("✅ No videos to retry!")
            return

        print(f"📝 Found {len(videos_without_transcripts)} videos to retry")
        print("🔄 Starting retry process...\n")

        success_count = 0
        failed_count = 0

        for idx, video in enumerate(videos_without_transcripts, 1):
            print(f"[{idx}/{len(videos_without_transcripts)}] {video.title[:60]}...")

            # Check if this video has previous errors
            previous_errors = db.query(TranscriptError).filter(
                TranscriptError.video_id == video.id
            ).all()

            if previous_errors:
                error_summary = ', '.join([e.error_type for e in previous_errors])
                print(f"  ℹ️  Previous errors: {error_summary}")

            transcript_data, error_data = transcript_fetcher.fetch_transcript(video.video_id)

            if transcript_data:
                db_transcript = Transcript(
                    video_id=video.id,
                    text=transcript_data['text'],
                    snippets=transcript_data['snippets'],
                    language_code=transcript_data['language_code'],
                    is_generated=transcript_data['is_generated']
                )
                db.add(db_transcript)

                # Delete previous errors for this video since we now have a transcript
                db.query(TranscriptError).filter(
                    TranscriptError.video_id == video.id
                ).delete()

                db.commit()
                success_count += 1
                print(f"  ✅ Transcript saved ({len(transcript_data['text'])} characters)")
            elif error_data:
                # Update or create error entry
                db_error = TranscriptError(
                    video_id=video.id,
                    error_type=error_data['error_type'],
                    error_message=error_data['error_message']
                )
                db.add(db_error)
                db.commit()
                failed_count += 1
                print(f"  ❌ Failed: {error_data['error_type']}")
            else:
                failed_count += 1
                print(f"  ❌ Failed with no error data")

        print("\n" + "="*60)
        print("✅ RETRY COMPLETE!")
        print(f"📊 Summary:")
        print(f"   - Total videos processed: {len(videos_without_transcripts)}")
        print(f"   - Successfully fetched: {success_count}")
        print(f"   - Failed: {failed_count}")
        print("="*60)

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(
        description='Retry fetching transcripts for videos that failed or are missing'
    )
    parser.add_argument(
        '--channel-url',
        help='Optional: Only retry for a specific channel URL',
        default=None
    )
    parser.add_argument(
        '--retry-all',
        action='store_true',
        help='Retry all videos without transcripts, including those with permanent errors'
    )
    parser.add_argument(
        '--retry-errors',
        help='Comma-separated list of specific error types to retry (e.g., RequestBlocked,IpBlocked)',
        default=None
    )

    args = parser.parse_args()
    retry_missing_transcripts(args.channel_url, args.retry_all, args.retry_errors)

if __name__ == "__main__":
    main()