#!/usr/bin/env python3
import sys
from backend.database import SessionLocal
from backend.search import SearchService

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test_search.py <search query>")
        sys.exit(1)

    query = ' '.join(sys.argv[1:])

    print(f"🔍 Searching for: '{query}'")
    print("="*60)

    db = SessionLocal()
    search_service = SearchService(db)

    try:
        results = search_service.search(query, limit=10)

        if not results:
            print("❌ No results found")
            print("\nTrying a simpler test query directly...")

            # Direct SQL test
            from backend.models import Transcript
            from sqlalchemy import func
            test = db.query(Transcript).filter(
                Transcript.text.ilike(f'%{query}%')
            ).first()

            if test:
                print(f"✅ Found '{query}' in transcript text (simple LIKE search works)")
                print("The issue might be with the full-text search query formatting")
            else:
                print(f"❌ '{query}' not found even with simple LIKE search")
        else:
            print(f"✅ Found {len(results)} results:\n")

            for idx, result in enumerate(results, 1):
                print(f"{idx}. {result['title']}")
                print(f"   Channel: {result['channel_name']}")
                print(f"   Match type: {result['match_type']}")
                print(f"   Rank: {result['rank']:.4f}")
                if result['timestamp']:
                    mins = int(result['timestamp'] // 60)
                    secs = int(result['timestamp'] % 60)
                    print(f"   Timestamp: {mins}:{secs:02d}")
                print(f"   Snippet: {result['snippet'][:150]}...")
                print(f"   URL: https://youtube.com/watch?v={result['video_id']}")
                print()

    finally:
        db.close()

if __name__ == "__main__":
    main()