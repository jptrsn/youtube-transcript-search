#!/usr/bin/env python3
"""
Local transcript fetcher - fetches transcripts using local IP and writes to remote DB via SSH tunnel
"""

import argparse
import sys
import os
import json
from pathlib import Path

# Add parent directory to path so we can import backend modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from fabric import Connection
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load .env.prod from the project root (parent of scripts/)
env_path = Path(__file__).parent.parent / '.env.prod'
load_dotenv(env_path)

# Then get the credentials
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_DB = os.getenv('POSTGRES_DB')

from backend.services.channel_service import ChannelService

def progress_callback(event: str, data: dict):
    """Simple text-based progress callback"""
    if event == 'status':
        print(f"  {data['message']}")
    elif event == 'channel_info':
        print(f"📺 Channel: {data['channel_name']}")
    elif event == 'videos_found':
        print(f"📹 Found {data['count']} videos")
    elif event == 'video_progress':
        print(f"  [{data['current']}/{data['total']}] {data['title'][:60]}...")
    elif event == 'video_status':
        if data['status'] == 'transcript_saved':
            length = data.get('length', 'unknown')
            print(f"    ✓ Saved transcript ({length} chars)")
        elif data['status'] == 'error':
            print(f"    ✗ Error: {data['error_type']}")
        elif data['status'] == 'has_transcript':
            print(f"    → Already has transcript")
    elif event == 'complete':
        new_transcripts = data.get('new_transcripts', 0)
        print(f"\n✅ Complete! {new_transcripts} new transcripts fetched")
    elif event == 'error':
        print(f"\n❌ Error: {data.get('message', 'Unknown error')}")

def get_postgres_ip(conn):
    """Get the IP address of the postgres container"""
    result = conn.run('docker inspect yt-transcript-db', hide=True)
    inspect_data = json.loads(result.stdout)

    # Get the IP address from the first network
    networks = inspect_data[0]['NetworkSettings']['Networks']
    # Get the first network's IP
    ip_address = list(networks.values())[0]['IPAddress']

    return ip_address

def main():
    parser = argparse.ArgumentParser(description='Fetch YouTube transcripts locally and write to remote DB')
    parser.add_argument('--ssh-host', required=True, help='SSH host (VPS IP or hostname)')
    parser.add_argument('--ssh-user', default='root', help='SSH username (default: root)')
    parser.add_argument('--ssh-key', default=None, help='SSH private key path (default: auto-detect)')
    parser.add_argument('--operation', required=True, choices=['fetch-missing', 'retry-failed'],
                        help='Operation to perform')
    parser.add_argument('--channel', required=True, help='Channel ID (e.g., UCxxx)')
    parser.add_argument('--limit', type=int, help='Limit number of videos to process')

    args = parser.parse_args()

    print(f"🔌 Connecting to {args.ssh_host}...")

    try:
        # Create SSH connection
        connect_kwargs = {}
        if args.ssh_key:
            connect_kwargs["key_filename"] = args.ssh_key

        conn = Connection(
            host=args.ssh_host,
            user=args.ssh_user,
            connect_kwargs=connect_kwargs
        )

        # Detect postgres container IP
        print(f"🔍 Detecting postgres container IP...")
        postgres_ip = get_postgres_ip(conn)
        print(f"✓ Found postgres at {postgres_ip}")

        # Create port forward (SSH tunnel)
        with conn.forward_local(5433, remote_host=postgres_ip, remote_port=5432):
            print(f"✓ SSH tunnel established (local port 5433)")

            # Create database connection through tunnel
            db_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@localhost:5433/{POSTGRES_DB}"
            engine = create_engine(db_url)
            SessionLocal = sessionmaker(bind=engine)
            db = SessionLocal()

            print(f"✓ Connected to remote database\n")

            # Create service with progress callback
            service = ChannelService(db, progress_callback=progress_callback)

            # Execute operation
            if args.operation == 'fetch-missing':
                print(f"🔍 Fetching missing transcripts for channel {args.channel}...\n")
                service.fetch_missing_transcripts(args.channel, limit=args.limit)
            elif args.operation == 'retry-failed':
                print(f"🔄 Retrying failed transcripts for channel {args.channel}...\n")
                service.retry_failed_transcripts(args.channel, limit=args.limit)

            db.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()