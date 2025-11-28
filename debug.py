#!/usr/bin/env python3
from backend.database import SessionLocal
from backend.models import Video, Transcript, Channel
from sqlalchemy import func

db = SessionLocal()

# Check counts
video_count = db.query(Video).count()
transcript_count = db.query(Transcript).count()
channel_count = db.query(Channel).count()

print(f"Channels: {channel_count}")
print(f"Videos: {video_count}")
print(f"Transcripts: {transcript_count}")

# Check if search vectors are populated
transcripts_with_vectors = db.query(Transcript).filter(
    Transcript.text_search_vector.isnot(None)
).count()

print(f"Transcripts with search vectors: {transcripts_with_vectors}")

# Sample a transcript to see if "welcome" exists anywhere
sample = db.query(Transcript).first()
if sample:
    print(f"\nSample transcript length: {len(sample.text)} characters")
    print(f"Contains 'welcome': {'welcome' in sample.text.lower()}")
    print(f"First 200 chars: {sample.text[:200]}")

db.close()